FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && \
    apt-get install -y \
    gcc \
    python3-dev \
    libffi-dev \
    pkg-config \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application
COPY src /app/src

# Expose the port
EXPOSE 8020

# Command to run the application
CMD ["uvicorn", "src.backend.main:app", "--host", "0.0.0.0", "--port", "8020"] 