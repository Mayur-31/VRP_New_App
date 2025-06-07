FROM osrm/osrm-backend:latest

# Update the sources list to use bullseye
RUN echo "deb http://deb.debian.org/debian bullseye main contrib non-free" > /etc/apt/sources.list

# Install wget for downloading the .pbf file
RUN apt-get update && apt-get install -y --allow-unauthenticated wget && rm -rf /var/lib/apt/lists/*

WORKDIR /data

# Download the .pbf file during build
RUN wget http://download.geofabrik.de/europe/united-kingdom-latest.osm.pbf -O united-kingdom-latest.osm.pbf

# Process the file during build
RUN osrm-extract united-kingdom-latest.osm.pbf -p /opt/car.lua
RUN osrm-partition united-kingdom-latest.osrm
RUN osrm-customize united-kingdom-latest.osrm

# Remove the .pbf file to reduce image size
RUN rm united-kingdom-latest.osm.pbf