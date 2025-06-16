FROM python:3.9-slim
LABEL service="vrp-app"
WORKDIR /app

# Install curl for health checks
RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .

# Use port 80 for Streamlit to match Kamal's proxy expectations
EXPOSE 80
HEALTHCHECK --interval=10s --timeout=5s --start-period=30s --retries=3 \
  CMD curl -f http://localhost:80/_stcore/health || exit 1
CMD ["streamlit", "run", "app.py", "--server.port=80", "--server.address=0.0.0.0"]
