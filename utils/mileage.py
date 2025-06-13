import re
import time
import requests
import pandas as pd
from tqdm import tqdm
from concurrent.futures import ThreadPoolExecutor
from functools import lru_cache
import os

POSTCODE_OVERRIDES = {
    'BD112BZ': (53.758755, -1.689026),
    'WA119TY': (53.476785, -2.666254)
}
POSTCODES_IO_URL = os.getenv("POSTCODES_IO_URL", "https://api.postcodes.io")
OSRM_URL = os.getenv("OSRM_URL", "http://osrm:5000")  # Use environment variable for OSRM

def is_valid_uk_postcode(postcode):
    pattern = (
        r'^([A-Za-z][A-Ha-hJ-Yj-y]?[0-9][A-Za-z0-9]? ?[0-9][A-Za-z]{2}|'
        r'[Gg][Ii][Rr] ?0[Aa]{2}|'
        r'[A-Za-z]{1,2}[0-9]{1,2} ?[0-9][A-Za-z]{2}|'
        r'[A-Za-z][0-9]{1,2} ?[0-9][A-Za-z]{2}|'
        r'[A-Za-z] ?[0-9][A-Za-z]{2})$'
    )
    return re.match(pattern, postcode.strip()) is not None

def clean_postcode(postcode):
    return str(postcode).strip().upper().replace(' ', '')

@lru_cache(maxsize=1000)
def get_coordinates_cached(postcode):
    cleaned_pc = clean_postcode(postcode)
    if cleaned_pc in POSTCODE_OVERRIDES:
        return POSTCODE_OVERRIDES[cleaned_pc]

    try:
        response = requests.get(f"{POSTCODES_IO_URL}/postcodes/{cleaned_pc}", timeout=3)
        if response.status_code == 200:
            return (response.json()['result']['latitude'],
                    response.json()['result']['longitude'])
        else:
            print(f"Failed to get coordinates for {postcode} from Postcodes.io: {response.status_code}")
            return (None, None)
    except Exception as e:
        print(f"Error getting coordinates for {postcode} from Postcodes.io: {e}")
        return (None, None)
    
def calculate_loaded_distance(args):
    start_coord, end_coord = args
    if None in start_coord + end_coord:
        return 0.0

    try:
        url = f"{OSRM_URL}/route/v1/driving/{start_coord[1]},{start_coord[0]};{end_coord[1]},{end_coord[0]}?overview=false"
        response = requests.get(url, timeout=5)
        if response.ok and response.json().get('code') == 'Ok':
            return response.json()['routes'][0]['distance'] / 1609.34
    except:
        return 0.0

def process_mileage_parallel(uploaded_file):
    """Main processing function with parallel execution"""
    raw_df = pd.read_csv(uploaded_file)
    df = raw_df.copy()

    df['COLLECTION POST CODE'] = df['COLLECTION POST CODE'].apply(clean_postcode)
    df['DELIVER POST CODE'] = df['DELIVER POST CODE'].apply(clean_postcode)

    # Parallel coordinate fetching
    with ThreadPoolExecutor(max_workers=8) as executor:
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

    # Parallel distance calculation
    with ThreadPoolExecutor(max_workers=8) as executor:
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

    # Calculate empty miles
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