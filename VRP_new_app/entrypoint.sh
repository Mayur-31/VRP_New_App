#!/bin/sh

# Function to wait for a service's health endpoint with timeout
wait_for_health() {
    url=$1
    timeout=60
    start_time=$(date +%s)
    echo "Waiting for $url to be healthy..."
    while ! curl -fs "$url" >/dev/null; do
        current_time=$(date +%s)
        elapsed=$((current_time - start_time))
        if [ $elapsed -ge $timeout ]; then
            echo "Timeout reached after $timeout seconds. Service not healthy."
            exit 1
        fi
        sleep 1
    done
    echo "$url is healthy!"
}

# Function to wait for OSRM service with timeout
wait_for_osrm() {
    timeout=60
    start_time=$(date +%s)
    echo "Waiting for OSRM to be ready..."
    while ! curl -fs 'http://osrm-service:5000/route/v1/driving/-0.127758,51.507351;-0.118092,51.502725?steps=true' >/dev/null; do
        current_time=$(date +%s)
        elapsed=$((current_time - start_time))
        if [ $elapsed -ge $timeout ]; then
            echo "Timeout reached after $timeout seconds. OSRM not ready."
            exit 1
        fi
        sleep 1
    done
    echo "OSRM is ready!"
}

# Wait for services
wait_for_health http://postcodes-service:8000/health
wait_for_osrm

# Start Streamlit
echo "All dependencies ready! Starting Streamlit..."
exec streamlit run app.py --server.port 8501 --server.address 0.0.0.0
