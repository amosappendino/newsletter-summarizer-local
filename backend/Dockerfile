# Use Python official image
FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy project files
COPY . .

COPY ./google_secrets.json /
ENV GOOGLE_APPLICATION_CREDENTIALS=/google_secrets.json

# Use a simpler CMD that doesn't rely on shell expansion
CMD exec uvicorn main:app --host 0.0.0.0 --port 8000

