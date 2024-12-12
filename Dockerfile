FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install curl for healthcheck
RUN apt-get update && \
    apt-get install -y curl && \
    rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Create static directory
RUN mkdir -p /app/static

# Copy the application
COPY src /app/src

# Create volume mount point for static files
VOLUME ["/app/static"]

# Expose the port
EXPOSE 8020

# Command to run the application
CMD ["uvicorn", "src.backend.main:app", "--host", "0.0.0.0", "--port", "8020"] 