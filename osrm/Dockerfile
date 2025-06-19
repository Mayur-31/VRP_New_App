# Use ARM64-compatible Ubuntu base image with LTS support
FROM ubuntu:22.04

# Install dependencies with default compiler
RUN apt-get update && \
    DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
        ca-certificates wget git && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Install libc-bin separately with version pinning
RUN apt-get update && \
    DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
        libc-bin=2.35-0ubuntu3.10 && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Install remaining packages in smaller batches
RUN apt-get update && \
    DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
        build-essential cmake pkg-config && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

RUN apt-get update && \
    DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
        libboost-all-dev liblua5.3-dev libstxxl-dev libtbb-dev && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

RUN apt-get update && \
    DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
        libbz2-dev libexpat1-dev zlib1g-dev && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Build OSRM
RUN git clone --depth 1 --branch v5.27.1 https://github.com/Project-OSRM/osrm-backend.git /osrm-src

WORKDIR /osrm-src

# Apply critical fixes
RUN find . -type f \( -name "*.cpp" -o -name "*.hpp" \) -exec sed -i '1s;^;#include <cstdint>\n#include <cstdlib>\n;' {} +
RUN sed -i 's/-Werror //g' CMakeLists.txt

# Apply Boost compatibility patch
RUN find . -type f -exec sed -i \
    -e 's/#include <boost\/function_output_iterator.hpp>/#include <boost\/iterator\/function_output_iterator.hpp>/g' \
    -e 's/#include <boost\/detail\/no_exceptions_support.hpp>/#include <boost\/core\/no_exceptions_support.hpp>/g' \
    -e 's/#include <boost\/bind.hpp>/#include <boost\/bind\/bind.hpp>\nusing namespace boost::placeholders;/g' \
    {} +

# Configure and build with reduced parallelism
WORKDIR /osrm-src/build
RUN cmake -DUSE_SYSTEM_TBB=ON \
          -DCMAKE_BUILD_TYPE=Release \
          -DENABLE_LTO=OFF \
          -DDISABLE_WERROR=ON \
          -DCMAKE_CXX_FLAGS="-O2 -Wno-deprecated-declarations -Wno-psabi -Wno-free-nonheap-object" .. && \
    cmake --build . -- -j$(($(nproc)/2)) && \
    cmake --install .

# Download and process UK map data
WORKDIR /data
RUN wget http://download.geofabrik.de/europe/united-kingdom-latest.osm.pbf -O uk.osm.pbf && \
    osrm-extract uk.osm.pbf -p /osrm-src/profiles/car.lua && \
    osrm-partition uk.osrm && \
    osrm-customize uk.osrm && \
    rm uk.osm.pbf

# Clean up
RUN rm -rf /osrm-src

# Start command
EXPOSE 5000
CMD ["osrm-routed", "--algorithm", "mld", "/data/uk.osrm"]
