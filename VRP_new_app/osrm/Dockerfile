FROM ubuntu:22.04 AS builder

# Install dependencies
RUN apt-get update && \
    apt-get install -y build-essential cmake git wget \
    libboost-dev libboost-filesystem-dev libboost-iostreams-dev \
    libboost-program-options-dev libboost-system-dev libboost-thread-dev \
    libbz2-dev liblua5.2-dev libstxxl-dev libxml2-dev libzip-dev

# Clone OSRM
RUN git clone https://github.com/Project-OSRM/osrm-backend.git
WORKDIR osrm-backend
RUN git checkout v5.25.0  # Use stable version

# Build OSRM
RUN mkdir build
WORKDIR build
RUN cmake .. -DCMAKE_BUILD_TYPE=Release
RUN cmake --build .
RUN cmake --build . --target install

# Create final image
FROM ubuntu:22.04
RUN apt-get update && \
    apt-get install -y libboost-system1.74.0 libboost-filesystem1.74.0 \
    libboost-iostreams1.74.0 libboost-program-options1.74.0 \
    libboost-thread1.74.0 libstxxl-dev libtbb-dev

COPY --from=builder /usr/local/bin /usr/local/bin
WORKDIR /data
ENTRYPOINT ["osrm-routed"]
