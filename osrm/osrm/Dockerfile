# Use ARM64-compatible Ubuntu base image
FROM --platform=linux/arm64 ubuntu:22.04

# Install dependencies
RUN apt-get update && \
    apt-get install -y wget build-essential cmake git libboost-all-dev liblua5.3-dev libstxxl-dev libtbb-dev && \
    rm -rf /var/lib/apt/lists/*

# Build OSRM from source
RUN git clone --depth 1 --branch v5.25.0 https://github.com/Project-OSRM/osrm-backend.git /osrm-src
WORKDIR /osrm-src
RUN mkdir build
WORKDIR /osrm-src/build
RUN cmake .. && \
    cmake --build . && \
    cmake --build . --target install

# Download and process UK map data
WORKDIR /data
RUN wget http://download.geofabrik.de/europe/united-kingdom-latest.osm.pbf -O uk.osm.pbf
RUN osrm-extract uk.osm.pbf -p /osrm-src/profiles/car.lua && \
    osrm-partition uk.osrm && \
    osrm-customize uk.osrm && \
    rm uk.osm.pbf

# Start command
EXPOSE 5000
CMD ["osrm-routed", "--algorithm", "mld", "/data/uk.osrm"]
