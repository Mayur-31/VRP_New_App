from ortools.constraint_solver import routing_enums_pb2, pywrapcp
import pandas as pd
import requests
import folium
import polyline
import time
import os

SPECIAL_POSTCODES = {
    'BD112BZ': (53.758755, -1.689026),
    'WA119TY': (53.476785, -2.666254),
    'DUBLIN': (53.3498, -6.2603)
}
OSRM_URL = os.getenv("OSRM_URL", "http://osrm:5000")  # Use environment variable for OSRM

def get_coordinates_for_map(postcode):
    if postcode in SPECIAL_POSTCODES:
        return SPECIAL_POSTCODES[postcode]
    try:
        response = requests.get(f"https://api.postcodes.io/postcodes/{postcode}", timeout=3)
        if response.status_code == 200:
            data = response.json()
            return (data['result']['latitude'], data['result']['longitude'])
    except Exception as e:
        print(f"Map geocoding error: {str(e)}")
    return None

def process_driver(driver, processed_df, all_postcodes, distance_matrix_list):
    try:
        driver_jobs = processed_df[processed_df["DRIVER NAME"] == driver]
        collection_pcs = driver_jobs["COLLECTION POST CODE"].dropna().unique()
        deliver_pcs = driver_jobs["DELIVER POST CODE"].dropna().unique()
        driver_postcodes = list(set(collection_pcs) | set(deliver_pcs))
        valid_postcodes = [pc for pc in driver_postcodes if pc in all_postcodes]

        if not valid_postcodes:
            return {}

        postcode_to_index = {pc: idx for idx, pc in enumerate(all_postcodes)}
        indices = [postcode_to_index[pc] for pc in valid_postcodes]
        cluster_matrix = [[distance_matrix_list[i][j] for j in indices] for i in indices]

        depot_pc = driver_jobs["COLLECTION POST CODE"].iloc[0]
        depot_index = valid_postcodes.index(depot_pc) if depot_pc in valid_postcodes else 0

        data = create_data_model(cluster_matrix, valid_postcodes, depot_index)
        route = solve_vrp_for_driver(data, driver)

        return {driver: route} if route else {}

    except Exception as e:
        print(f"Error processing driver {driver}: {str(e)}")
        return {}

def create_data_model(distance_matrix, postcodes, depot_index):
    return {
        "distance_matrix": distance_matrix,
        "num_vehicles": 1,
        "depot": depot_index,
        "postcodes": postcodes
    }

def solve_vrp_for_driver(data, driver_name):
    try:
        manager = pywrapcp.RoutingIndexManager(
            len(data["distance_matrix"]),
            data["num_vehicles"],
            data["depot"]
        )
        routing = pywrapcp.RoutingModel(manager)

        def distance_callback(from_index, to_index):
            from_node = manager.IndexToNode(from_index)
            to_node = manager.IndexToNode(to_index)
            return data["distance_matrix"][from_node][to_node]

        transit_callback_index = routing.RegisterTransitCallback(distance_callback)
        routing.SetArcCostEvaluatorOfAllVehicles(transit_callback_index)

        routing.AddDimension(
            transit_callback_index,
            0,
            3000000,
            True,
            "Distance"
        )
        distance_dimension = routing.GetDimensionOrDie("Distance")
        distance_dimension.SetGlobalSpanCostCoefficient(100)

        search_parameters = pywrapcp.DefaultRoutingSearchParameters()
        search_parameters.first_solution_strategy = (
            routing_enums_pb2.FirstSolutionStrategy.AUTOMATIC
        )
        search_parameters.local_search_metaheuristic = (
            routing_enums_pb2.LocalSearchMetaheuristic.GREEDY_DESCENT
        )
        search_parameters.time_limit.seconds = 10

        solution = routing.SolveWithParameters(search_parameters)
        if solution:
            return get_route(data, manager, routing, solution)
        return None
    except Exception as e:
        print(f"VRP solving error for {driver_name}: {str(e)}")
        return None

def get_route(data, manager, routing, solution):
    route = []
    index = routing.Start(0)
    while not routing.IsEnd(index):
        node = data["postcodes"][manager.IndexToNode(index)]
        route.append(node)
        index = solution.Value(routing.NextVar(index))
    route.append(data["postcodes"][manager.IndexToNode(index)])
    return route

def visualize_routes(driver_routes, get_coordinates_func, jobs_df, selected_driver=None, output_html='driver_routes.html'):
    m = folium.Map(location=[54.0, -2.0], zoom_start=6)
    colors = ['red', 'blue', 'green', 'purple', 'orange', 'darkred', 'darkblue',
              'darkgreen', 'cadetblue', 'pink']

    for i, (driver, route) in enumerate(driver_routes.items()):
        if selected_driver and driver != selected_driver:
            continue
        if not route:
            continue
        color = colors[i % len(colors)]
        fg = folium.FeatureGroup(name=driver, show=True if selected_driver else False)
        coords = [get_coordinates_func(pc) for pc in route]

        driver_jobs = jobs_df[jobs_df["DRIVER NAME"] == driver]
        if driver_jobs.empty:
            print(f"No jobs found for {driver}")
            continue

        job_schedule_html = driver_jobs[[
            "DAY", "DATE", "CUSTOMER", "JOB TYPE", "COLLECTION POST CODE",
            "DELIVER POST CODE", "ON DOOR TIME", "DEPARTURE TIME", "ARRIVAL TIME",
            "RUN TIME", "LOADED MILES", "EMPTY MILES", "TOTAL MILES"
        ]].to_html(index=False, justify="center")

        path_coords = []
        previous_valid_coord = None
        for pc, coord in zip(route, coords):
            if coord is None:
                previous_valid_coord = None
                continue

            if previous_valid_coord is not None:
                try:
                    url = f"{OSRM_URL}/route/v1/driving/{previous_valid_coord[1]},{previous_valid_coord[0]};{coord[1]},{coord[0]}?overview=full"
                    response = requests.get(url)
                    data = response.json()
                    if response.status_code == 200 and data.get('code') == 'Ok':
                        decoded = polyline.decode(data['routes'][0]['geometry'])
                        path_coords.extend(decoded)
                    else:
                        path_coords.extend([previous_valid_coord, coord])
                except Exception as e:
                    print(f"Error getting route for {driver}: {e}")
                    path_coords.extend([previous_valid_coord, coord])
                time.sleep(1)

            previous_valid_coord = coord

        if path_coords:
            folium.PolyLine(
                locations=path_coords,
                color=color,
                weight=2.5,
                opacity=1,
                popup=driver
            ).add_to(fg)

        for idx, (pc, coord) in enumerate(zip(route, coords)):
            if coord is None:
                continue

            position = idx + 1
            if idx == 0:
                start_popup_html = f"<b>1. {pc}</b><br><br>{job_schedule_html}"
                folium.Marker(
                    location=coord,
                    popup=folium.Popup(start_popup_html, max_width=400),
                    icon=folium.Icon(color='green', icon='play')
                ).add_to(fg)
            elif idx == len(route) - 1:
                if pc != route[0]:
                    folium.Marker(
                        location=coord,
                        popup=folium.Popup(job_schedule_html, max_width=400),
                        icon=folium.Icon(color='red', icon='stop')
                    ).add_to(fg)
            else:
                folium.Marker(
                    location=coord,
                    popup=f"{position}. {pc}",
                    icon=folium.Icon(color=color)
                ).add_to(fg)

        fg.add_to(m)

    folium.LayerControl(collapsed=False).add_to(m)
    m.save(output_html)
    print(f"Map saved as '{output_html}'")
