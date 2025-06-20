FROM python:3.9-slim

WORKDIR /app

# Install build tools, wait-for-it, and curl for health checks
RUN apt-get update && apt-get install -y build-essential wait-for-it curl

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .

# Add health check script
COPY config/healthcheck.sh /healthcheck.sh
RUN chmod +x /healthcheck.sh

# Add health check
HEALTHCHECK --interval=5s --timeout=3s \
  CMD /healthcheck.sh || exit 1

# Run on port 80 instead of 8501
CMD ["streamlit", "run", "app.py", "--server.port=80", "--server.address=0.0.0.0"]
