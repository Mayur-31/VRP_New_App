FROM python:3.9-slim

WORKDIR /app

# Install dependencies
RUN apt-get update && apt-get install -y build-essential wait-for-it curl

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .

# Add health check script
COPY config/healthcheck.sh /healthcheck.sh
RUN chmod +x /healthcheck.sh

# Health check with dependency verification
HEALTHCHECK --interval=5s --timeout=3s \
  CMD /healthcheck.sh || exit 1

# Wait for dependencies before starting
CMD wait-for-it -t 30 osrm:5000 postcodes-app:8000 -- \
    streamlit run app.py --server.port=80 --server.address=0.0.0.0
