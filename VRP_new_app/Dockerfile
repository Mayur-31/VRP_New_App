FROM python:3.9-slim

# Install dependencies - FIXED: Use netcat-openbsd instead of netcat
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    netcat-openbsd  # Changed from netcat to netcat-openbsd

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Add healthcheck and entrypoint
COPY config/healthcheck.sh /healthcheck.sh
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /healthcheck.sh /entrypoint.sh

# Set entrypoint and healthcheck
ENTRYPOINT ["/entrypoint.sh"]
HEALTHCHECK --interval=15s --timeout=5s --start-period=60s \
    CMD curl -fs http://localhost:8501/_stcore/health || exit 1
