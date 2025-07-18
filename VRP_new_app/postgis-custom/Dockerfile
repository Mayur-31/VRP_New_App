FROM postgres:15-alpine

# Install build dependencies and libraries, including llvm
RUN apk add --no-cache --virtual .build-deps \
      build-base \
      curl \
      perl \
      clang \
      llvm \
      sed \
      postgresql15-dev \
      postgresql15-contrib \
      geos \
      geos-dev \
      gdal \
      gdal-dev \
      proj \
      proj-dev \
      libxml2-dev \
      json-c \
      json-c-dev \
      protobuf-c \
      protobuf-c-dev \
    && ln -s /usr/bin/clang /usr/bin/clang-19 \
    && mkdir -p /usr/lib/llvm19/bin \
    && ln -s /usr/bin/llvm-lto /usr/lib/llvm19/bin/llvm-lto \
    && rm -rf /var/cache/apk/*

ENV POSTGIS_VERSION=3.4.0

# Download, configure (disabling LTO), build and install PostGIS
RUN curl -L "https://download.osgeo.org/postgis/source/postgis-${POSTGIS_VERSION}.tar.gz" \
      -o postgis.tar.gz \
    && tar xzf postgis.tar.gz \
    && cd postgis-${POSTGIS_VERSION} \
    && ./configure \
         --without-raster \
         --disable-lto \
         CFLAGS="-O2" \
    && make \
    && make install \
    && cd .. \
    && rm -rf postgis-${POSTGIS_VERSION} postgis.tar.gz

# Copy any init scripts
COPY initdb/10_postgis.sh /docker-entrypoint-initdb.d/10_postgis.sh
RUN chmod +x /docker-entrypoint-initdb.d/10_postgis.sh
