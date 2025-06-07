FROM python:3.9-slim

WORKDIR /app

# Install build tools and wait-for-it
RUN apt-get update && apt-get install -y build-essential wait-for-it

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]
