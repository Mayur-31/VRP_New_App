import re
import time
import requests
import pandas as pd
from tqdm import tqdm
from concurrent.futures import ThreadPoolExecutor
from functools import lru_cache
import os
import tenacity

POSTCODE_OVERRIDES = {
    'BD11 2BZ': (53.758755, -1.689026),
    'WA11 9TY': (53.476785, -2.666254),
    'DUBLIN': (53.349805, -6.26031)
}
POSTCODES_IO_URL = os.getenv("POSTCODES_IO_URL", "http://postcodes-service:8000")
OSRM_URL = os.getenv("OSRM_URL", "http://osrm:5000")

def is_valid_special_postcode(postcode):
    cleaned = clean_postcode(postcode)
    return cleaned in POSTCODE_OVERRIDES

def is_valid_uk_postcode(postcode):
    pattern = (
        r'^([A-Za-z][A-Ha-hJ-Yj-y]?[0-9][A-Za-z0-9]? ?[0-9][A-Za-z]{2}|'
        r'[Gg][Ii][Rr] ?0[Aa]{2}|'
        r'[A-Za-z]{1,2}[0-9]{1,2} ?[0-9][A-Za-z]{2}|'
        r'[A-Za-z][0-9]{1,2} ?[0-9][A-Za-z]{2}|'
        r'[A-Za-z] ?[0-9][A-Za-z]{2})$'
    )
    return re.match(pattern, postcode.strip()) is not None

def is_valid_postcode(postcode):
    return is_valid_uk_postcode(postcode) or is_valid_special_postcode(postcode)

def format_postcode(postcode):
    cleaned = clean_postcode(postcode)
    if is_valid_uk_postcode(cleaned):
        return f"{cleaned[:-3]} {cleaned[-3:]}"
    return cleaned

def check_postcode_in_db(postcode):
    cleaned_pc = clean_postcode(postcode)
    formatted_pc = format_postcode(postcode)
    if cleaned_pc in POSTCODE_OVERRIDES:
        print(f"Postcode {cleaned_pc} found in POSTCODE_OVERRIDES")
        return True

    for pc in [cleaned_pc, formatted_pc]:
        try:
            url = f"{POSTCODES_IO_URL}/postcodes/{pc}"
            print(f"Querying API for postcode: {pc}, URL: {url}")
            response = requests.get(url, timeout=5)
            print(f"API response for {pc}: status={response.status_code}, content={response.text}")
            if response.status_code == 200:
                try:
                    data = response.json()
                    if 'latitude' in data and 'longitude' in data:
                        print(f"Postcode {pc} found in database")
                        return True
                except ValueError:
                    print(f"Invalid JSON response for {pc}: {response.text}")
            else:
                print(f"Postcode {pc} not found, status code: {response.status_code}")
        except requests.RequestException as e:
            print(f"Error querying API for {pc}: {str(e)}")
    print(f"Postcode {cleaned_pc} not found in database")
    return False

def clean_postcode(postcode):
    return str(postcode).strip().upper().replace(' ', '')

@tenacity.retry(
    stop=tenacity.stop_after_attempt(3),
    wait=tenacity.wait_exponential(multiplier=1, min=1, max=10),
    retry=tenacity.retry_if_exception_type(requests.RequestException),
)
@lru_cache(maxsize=1000)
def get_coordinates_cached(postcode):
    cleaned_pc = clean_postcode(postcode)
    if not is_valid_postcode(cleaned_pc):
        print(f"Invalid postcode format: {cleaned_pc}")
        return (None, None)
    if cleaned_pc in POSTCODE_OVERRIDES:
        return POSTCODE_OVERRIDES[cleaned_pc]

    try:
        formatted_pc = format_postcode(cleaned_pc)
        url = f"{POSTCODES_IO_URL}/postcodes/{formatted_pc}"
        print(f"Fetching coordinates for {formatted_pc}, URL: {url}")
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        if 'latitude' in data and 'longitude' in data:
            print(f"Coordinates for {formatted_pc}: ({data['latitude']}, {data['longitude']})")
            return (data['latitude'], data['longitude'])
        else:
            print(f"No valid coordinates for {formatted_pc}: {data}")
            return (None, None)
    except requests.exceptions.RequestException as e:
        print(f"Error fetching coordinates for {formatted_pc}: {str(e)}")
        return (None, None)

def calculate_loaded_distance(args):
    start_coord, end_coord = args
    if None in start_coord + end_coord:
        return 0.0

    try:
        url = f"{OSRM_URL}/route/v1/driving/{start_coord[1]},{start_coord[0]};{end_coord[1]},{end_coord[0]}?overview=false"
        response = requests.get(url, timeout=10)
        if response.ok and response.json().get('code') == 'Ok':
            return response.json()['routes'][0]['distance'] / 1609.34
    except:
        return 0.0

def process_mileage_parallel(uploaded_file):
    try:
        # Added debug info
        print(f"Processing file of size: {len(uploaded_file.getvalue())} bytes")
        raw_df = pd.read_csv(uploaded_file)
        print(f"Successfully read CSV with {len(raw_df)} rows")
        
    except Exception as e:
        # Enhanced error logging
        print(f"Error reading CSV: {str(e)}")
        print(f"File content sample: {uploaded_file.getvalue()[:200]}...")
        raise

    df = raw_df.copy()

    df['COLLECTION POST CODE'] = df['COLLECTION POST CODE'].apply(clean_postcode)
    df['DELIVER POST CODE'] = df['DELIVER POST CODE'].apply(clean_postcode)

    with ThreadPoolExecutor(max_workers=4) as executor:
        collection_coords = list(tqdm(
            executor.map(get_coordinates_cached, df['COLLECTION POST CODE']),
            total=len(df),
            desc="Fetching Collection Coordinates"
        ))

        delivery_coords = list(tqdm(
            executor.map(get_coordinates_cached, df['DELIVER POST CODE']),
            total=len(df),
            desc="Fetching Delivery Coordinates"
        ))

    with ThreadPoolExecutor(max_workers=4) as executor:
        loaded_distances = list(tqdm(
            executor.map(calculate_loaded_distance, zip(collection_coords, delivery_coords)),
            total=len(df),
            desc="Calculating Loaded Miles"
        ))

    df['LOADED MILES'] = loaded_distances
    df['DEPARTURE_DATETIME'] = pd.to_datetime(
        df['DATE'] + ' ' + df['DEPARTURE TIME'],
        dayfirst=True,
        errors='coerce'
    )
    df.sort_values(['DRIVER NAME', 'DEPARTURE_DATETIME'], inplace=True)

    driver_locations = {}
    empty_distances = []

    for idx, row in tqdm(df.iterrows(), total=len(df), desc="Calculating Empty Miles"):
        driver = row['DRIVER NAME']
        current_collection = collection_coords[idx]

        if driver in driver_locations:
            previous_delivery = driver_locations[driver]
            if None not in previous_delivery + current_collection:
                empty_dist = calculate_loaded_distance((previous_delivery, current_collection))
                empty_distances.append(empty_dist)
            else:
                empty_distances.append(0.0)
        else:
            empty_distances.append(0.0)

        driver_locations[driver] = delivery_coords[idx]

    df['EMPTY MILES'] = empty_distances
    df['TOTAL MILES'] = df['LOADED MILES'] + df['EMPTY MILES']

    return raw_df, df
