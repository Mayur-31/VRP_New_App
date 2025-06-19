# Stage 1: Get QEMU for ARM64 emulation
FROM multiarch/qemu-user-static:latest AS qemu

# Stage 2: Main image
FROM python:3.10-slim-bullseye

# Copy QEMU static binary
COPY --from=qemu /usr/bin/qemu-aarch64-static /usr/bin/

LABEL service="vrp-app"
WORKDIR /app

# Install system dependencies
RUN apt-get update && \
    apt-get install -y curl && \
    rm -rf /var/lib/apt/lists/*

# Install Python packages
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Remove QEMU after installations
RUN rm /usr/bin/qemu-aarch64-static

COPY . .
EXPOSE 80
HEALTHCHECK --interval=10s --timeout=5s --start-period=30s --retries=3 \
  CMD curl -f http://localhost:80/_stcore/health || exit 1
CMD ["streamlit", "run", "app.py", "--server.port=80", "--server.address=0.0.0.0"]
