# utils/distance_matrix.py

import numpy as np
import pandas as pd
import time
import requests
from geopy.geocoders import Nominatim
from geopy.extra.rate_limiter import RateLimiter

PREDEFINED_COORDS = {
    'BD112BZ': (53.758755, -1.689026),
    'WA119TY': (53.476785, -2.666254)
}

def geocode_postcodes(postcodes):
    """
    Returns a dict mapping each postcode to its (lat, lon)
    """
    geolocator = Nominatim(user_agent="vrp_solver", timeout=10)
    geocode = RateLimiter(geolocator.geocode, min_delay_seconds=1, max_retries=3)
    postcode_lookup = {}
    for pc in postcodes:
        if pc in PREDEFINED_COORDS:
            postcode_lookup[pc] = PREDEFINED_COORDS[pc]
        else:
            try:
                location = geocode(f"{pc}, UK", exactly_one=True)
                if location and 'United Kingdom' in location.address:
                    postcode_lookup[pc] = (location.latitude, location.longitude)
                else:
                    postcode_lookup[pc] = (np.nan, np.nan)
            except Exception as e:
                print(f"Error geocoding {pc}: {e}")
                postcode_lookup[pc] = (np.nan, np.nan)
    return postcode_lookup

def create_osrm_distance_matrix(postcode_lookup, batch_size=50):
    """
    Builds a driving distance matrix (in miles) using OSRM.
    """
    valid_items = [
        (pc, lat, lon) for pc, (lat, lon) in postcode_lookup.items()
        if not (pd.isna(lat) or pd.isna(lon)) and (49.9 < lat < 60.9) and (-8.6 < lon < 1.9)
    ]
    if not valid_items:
        raise ValueError("No valid UK coordinates found.")

    postcodes, lats, lons = zip(*valid_items)
    N = len(postcodes)
    distance_matrix = np.full((N, N), np.nan)

    batches = [list(range(i, min(i + batch_size, N))) for i in range(0, N, batch_size)]

    def get_submatrix(batch_i, batch_j):
        if batch_i == batch_j:
            indices = batches[batch_i]
            sources = destinations = ';'.join(map(str, range(len(indices))))
        else:
            indices = batches[batch_i] + batches[batch_j]
            sources = ';'.join(map(str, range(len(batches[batch_i]))))
            destinations = ';'.join(map(str, range(len(batches[batch_i]), len(indices))))
        coords_str = ";".join([f"{lons[k]},{lats[k]}" for k in indices])
        url = f"http://osrm:5000/table/v1/driving/{coords_str}?annotations=distance&sources={sources}&destinations={destinations}"
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        distances_meters = response.json()['distances']
        distances_miles = (np.array(distances_meters) * 0.000621371)
        return distances_miles, batches[batch_i], batches[batch_j] if batch_i != batch_j else batches[batch_i]

    for i in range(len(batches)):
        submatrix, rows, cols = get_submatrix(i, i)
        distance_matrix[np.ix_(rows, cols)] = submatrix
        time.sleep(1)
    for i in range(len(batches)):
        for j in range(i + 1, len(batches)):
            submatrix, rows, cols = get_submatrix(i, j)
            distance_matrix[np.ix_(rows, cols)] = submatrix
            distance_matrix[np.ix_(cols, rows)] = submatrix.T
            time.sleep(1)
    return pd.DataFrame(distance_matrix, index=postcodes, columns=postcodes)