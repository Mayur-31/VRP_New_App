FROM osrm/osrm-backend:latest

# Update the sources list to use bullseye
RUN echo "deb http://deb.debian.org/debian bullseye main contrib non-free" > /etc/apt/sources.list

# Update package list and install wget, curl, and netcat-openbsd, bypassing authentication
RUN apt-get update && apt-get install -y --allow-unauthenticated wget curl netcat-openbsd && rm -rf /var/lib/apt/lists/*

WORKDIR /data
COPY . /data