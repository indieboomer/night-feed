FROM python:3.11-slim

WORKDIR /app

# Install docker CLI for executing other containers
RUN apt-get update && \
    apt-get install -y docker.io && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Create necessary directories
RUN mkdir -p /data /output /config

ENV TZ=Europe/Warsaw

CMD ["python", "-u", "orchestrator.py"]
