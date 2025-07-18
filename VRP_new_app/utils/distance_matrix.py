import numpy as np
import pandas as pd
import time
import requests
from .mileage import get_coordinates_cached, POSTCODE_OVERRIDES, POSTCODES_IO_URL
import os
import tenacity

PREDEFINED_COORDS = POSTCODE_OVERRIDES

OSRM_URL = os.getenv("OSRM_URL", "http://osrm:5000")

def geocode_postcodes(postcodes):
    postcode_lookup = {}
    for pc in postcodes:
        if pc in PREDEFINED_COORDS:
            postcode_lookup[pc] = PREDEFINED_COORDS[pc]
        else:
            coords = get_coordinates_cached(pc)
            postcode_lookup[pc] = coords if coords != (None, None) else (np.nan, np.nan)
    return postcode_lookup

def create_osrm_distance_matrix(postcode_lookup, batch_size=50):
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

    @tenacity.retry(
        stop=tenacity.stop_after_attempt(3),
        wait=tenacity.wait_exponential(multiplier=1, min=1, max=10),
        retry=tenacity.retry_if_exception_type(requests.exceptions.RequestException),
    )
    def get_submatrix(batch_i, batch_j):
        if batch_i == batch_j:
            indices = batches[batch_i]
            sources = destinations = ';'.join(map(str, range(len(indices))))
        else:
            indices = batches[batch_i] + batches[batch_j]
            sources = ';'.join(map(str, range(len(batches[batch_i]))))
            destinations = ';'.join(map(str, range(len(batches[batch_i]), len(indices))))
        coords_str = ";".join([f"{lons[k]},{lats[k]}" for k in indices])
        url = f"{OSRM_URL}/table/v1/driving/{coords_str}?annotations=distance&sources={sources}&destinations={destinations}"
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
