FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies and Rust
RUN apt-get update && \
    apt-get install -y \
    curl \
    gcc \
    python3-dev \
    libffi-dev \
    pkg-config \
    && curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y \
    && rm -rf /var/lib/apt/lists/*

# Add cargo to PATH
ENV PATH="/root/.cargo/bin:${PATH}"

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