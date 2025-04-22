import streamlit as st
import pandas as pd
import tempfile, io, time
from concurrent.futures import ThreadPoolExecutor
from utils import mileage, distance_matrix, route_optimization

st.set_page_config(page_title="🚛 Smart Route Optimizer", layout="wide", page_icon=":truck:")

# Set API key for mileage module
mileage.set_api_key(st.secrets["OPENCAGE_API_KEY"])

def load_css():
    try:
        with open("assets/style.css") as f:
            st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)
    except FileNotFoundError:
        st.warning("Warning: style.css not found. Using default Streamlit styling.")

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
    st.markdown("### Deliver faster, route smarter")

    uploaded_file = st.file_uploader("**Upload CSV File**", type=["csv"])
    if not uploaded_file:
        return

    start_time = time.time()
    with st.spinner("🚀 Processing file…"):
        file_bytes = uploaded_file.read()
        raw_df, processed_df = get_mileage(file_bytes)
        unique_pcs = tuple(pd.unique(
            processed_df[['COLLECTION POST CODE','DELIVER POST CODE']].values.ravel()
        ))
        dist_matrix_df = get_distance_matrix(unique_pcs)

    elapsed = time.time() - start_time
    st.success(f"Data loaded and cached in {elapsed:.1f}s!")

    # Performance metrics & data download
    total_loaded = processed_df['LOADED MILES'].sum()
    total_empty = processed_df['EMPTY MILES'].sum()
    st.subheader("📈 Summary Metrics")
    st.metric("Total Loaded", f"{total_loaded:.1f} mi")
    st.metric("Total Empty", f"{total_empty:.1f} mi")
    st.metric("Grand Total", f"{total_loaded + total_empty:.1f} mi")
    st.download_button(
        "💾 Download Processed CSV",
        processed_df.to_csv(index=False).encode(),
        "optimized_routes.csv",
        "text/csv"
    )

    # Select a single driver to optimize on demand
    drivers = processed_df["DRIVER NAME"].unique().tolist()
    selected = st.selectbox("Select a driver to view route details", drivers)

    if selected:
        with st.spinner(f"🤖 Solving VRP for {selected}…"):
            # process_driver returns { driver_name: [route sequence] }
            dr = route_optimization.process_driver(
                selected,
                processed_df,
                list(dist_matrix_df.index),
                (dist_matrix_df.values * 1000).round().astype(int).tolist()
            )
        route = dr.get(selected, [])
        if not route:
            st.error("No valid route found for this driver.")
        else:
            # compute total miles from distance matrix (which is in miles)
            total_miles = sum(
                dist_matrix_df.loc[route[i], route[i+1]]
                for i in range(len(route)-1)
            )
            st.subheader(f"Driver: {selected}")
            st.markdown(f"**Route:** {' → '.join(route)} \n**Total Distance:** {total_miles:.2f} mi")

            # mini‐map for this driver only
            tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".html")
            route_optimization.visualize_routes(
                {selected: route},
                route_optimization.get_coordinates_for_map,
                processed_df,
                output_html=tmp.name
            )
            html = open(tmp.name, "r").read()
            st.subheader("🗺 Driver Route Map")
            st.components.v1.html(html, height=600)

if __name__ == "__main__":
    main()
