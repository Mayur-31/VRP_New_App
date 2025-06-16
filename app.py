import streamlit as st
import pandas as pd
import tempfile, io, time
from concurrent.futures import ThreadPoolExecutor
import folium
import requests
import polyline
from folium.plugins import PolyLineTextPath
from utils import mileage, distance_matrix, route_optimization
import os
STREAMLIT_PORT = os.getenv("STREAMLIT_SERVER_PORT", "8501")

st.set_page_config(page_title="🚚 Smart Vehicle Routing Optimizer", layout="wide", page_icon=":truck:")
OSRM_URL = os.getenv("OSRM_URL", "http://osrm:5000")  # Use environment variable for OSRM

def load_css():
    with open("assets/style.css") as f:
        st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)

load_css()

@st.cache_data(show_spinner=False)
def get_mileage(file_bytes):
    raw_df, processed_df = mileage.process_mileage_parallel(io.BytesIO(file_bytes))
    return raw_df, processed_df

@st.cache_data(show_spinner=False)
def get_distance_matrix(unique_pcs):
    lookup = distance_matrix.geocode_postcodes(unique_pcs)
    return distance_matrix.create_osrm_distance_matrix(lookup)

def main():
    st.title("🚚 Smart Vehicle Routing Optimizer")
    st.markdown(f"### Running on port {STREAMLIT_PORT}")

    uploaded_file = st.file_uploader("**🚚 Upload CSV File**", type=["csv"])
    if not uploaded_file:
        return

    # Load and process data
    start_time = time.time()
    with st.spinner("🚀 Processing file…"):
        file_bytes = uploaded_file.read()
        raw_df, df = get_mileage(file_bytes)
        unique_pcs = tuple(pd.unique(
            df[['COLLECTION POST CODE','DELIVER POST CODE']].values.ravel()
        ))
        dist_matrix_df = get_distance_matrix(unique_pcs)
    elapsed = time.time() - start_time
    st.success(f"Data loaded and cached in {elapsed:.1f}s!")

    # Summary metrics
    total_loaded = df['LOADED MILES'].sum()
    total_empty  = df['EMPTY MILES'].sum()
    st.subheader("📈 Summary Metrics")
    st.metric("Total Loaded", f"{total_loaded:.1f} mi")
    st.metric("Total Empty",  f"{total_empty:.1f} mi")
    st.metric("Grand Total",  f"{total_loaded + total_empty:.1f} mi")
    st.download_button(
        "💾 Download Processed CSV",
        df.to_csv(index=False).encode(),
        "optimized_routes.csv",
        "text/csv"
    )

    # Option: show empty miles breakdown per driver
    if st.checkbox("Show empty miles by driver"):
        empty_by_driver = (
            df.groupby("DRIVER NAME")["EMPTY MILES"]
              .sum()
              .reset_index()
              .rename(columns={"EMPTY MILES": "Total Empty Miles"})
        )
        st.dataframe(empty_by_driver)

    # Select a driver for empty miles map
    drivers = df["DRIVER NAME"].unique().tolist()
    selected_driver_for_map = st.selectbox("Select a driver to view empty miles map", drivers)

    # Option: map empty-mile segments with directional arrows for selected driver
    if st.checkbox("Show empty-mile segments on map for selected driver"):
        df_map = df[df["DRIVER NAME"] == selected_driver_for_map].copy()
        df_map['DATETIME'] = pd.to_datetime(
            df_map['DATE'] + ' ' + df_map['DEPARTURE TIME'], dayfirst=True, errors='coerce'
        )
        df_map.sort_values(['DRIVER NAME', 'DATETIME'], inplace=True)
        df_map['PREV_DELIVER'] = df_map.groupby('DRIVER NAME')['DELIVER POST CODE'].shift()

        m = folium.Map(location=[54.0, -2.0], zoom_start=6)
        for _, row in df_map.iterrows():
            prev_pc = row['PREV_DELIVER']
            curr_pc = row['COLLECTION POST CODE']
            if pd.notna(prev_pc) and prev_pc in dist_matrix_df.index:
                start = route_optimization.get_coordinates_for_map(prev_pc)
                end   = route_optimization.get_coordinates_for_map(curr_pc)
                if start and end:
                    coords_str = f"{start[1]},{start[0]};{end[1]},{end[0]}"
                    url = f"{OSRM_URL}/route/v1/driving/{coords_str}?overview=full&geometries=polyline"
                    try:
                        resp = requests.get(url, timeout=10)
                        data = resp.json()
                        if resp.status_code == 200 and data.get('code') == 'Ok':
                            path = polyline.decode(data['routes'][0]['geometry'])
                            pl = folium.PolyLine(
                                locations=path,
                                color='red',
                                weight=2,
                                popup=(f"Driver: {row['DRIVER NAME']}<br>Empty miles: {row['EMPTY MILES']:.1f}")
                            )
                            m.add_child(pl)
                            # Add directional arrows along path
                            arrow = PolyLineTextPath(
                                pl,
                                '►',
                                repeat=True,
                                offset=7,
                                attributes={'fill': 'red', 'font-weight': 'bold', 'font-size': '12'}
                            )
                            m.add_child(arrow)
                    except Exception as e:
                        print(f"OSRM error for empty segment: {e}")
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix='.html')
        m.save(tmp.name)
        st.subheader(f"🗺 Empty-Mile Segments Map for {selected_driver_for_map} (road paths with direction)")
        st.components.v1.html(open(tmp.name).read(), height=600)

    # Select a single driver to optimize on demand
    selected_driver_for_route = st.selectbox("Select a driver to view route details", drivers)

    if selected_driver_for_route:
        with st.spinner(f"🤖 Solving VRP for {selected_driver_for_route}…"):
            dr = route_optimization.process_driver(
                selected_driver_for_route,
                df,
                list(dist_matrix_df.index),
                (dist_matrix_df.values * 1000).round().astype(int).tolist()
            )
        route = dr.get(selected_driver_for_route, [])
        if not route:
            st.error("No valid route found for this driver.")
        else:
            total_miles = sum(
                dist_matrix_df.loc[route[i], route[i+1]]
                for i in range(len(route)-1)
            )
            st.subheader(f"Driver: {selected_driver_for_route}")
            st.markdown(f"**Route:**  {' → '.join(route)}  \n**Total Distance:** {total_miles:.2f} mi")

            tmp_map = tempfile.NamedTemporaryFile(delete=False, suffix='.html')
            route_optimization.visualize_routes(
                {selected_driver_for_route: route},
                route_optimization.get_coordinates_for_map,
                df,
                output_html=tmp_map.name
            )
            st.subheader("🗺 Driver Route Map")
            st.components.v1.html(open(tmp_map.name).read(), height=600)

if __name__ == "__main__":
    main()