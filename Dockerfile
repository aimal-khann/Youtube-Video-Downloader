FROM python:3.11-slim

# Install system dependencies: FFmpeg, Node.js and certificates
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    nodejs \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install python packages
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy project files
COPY . .

# Railway provides $PORT at runtime
ENV PORT=8000
EXPOSE 8000

# Start server via main.py
CMD ["python", "main.py"]
