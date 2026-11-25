FROM python:3.11-slim

# Install system dependencies for OpenCV, audio and TLS
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 \
    libglib2.0-0 \
    libgomp1 \
    ffmpeg \
    curl \
    openssl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python requirements (install CPU torch first to avoid downloading 3+ GB of CUDA wheels)
COPY requirements.txt .
RUN pip install --no-cache-dir --extra-index-url https://download.pytorch.org/whl/cpu torch torchvision && \
    pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY app/ ./app/
COPY static/ ./static/
COPY models/ ./models/
COPY testdata/ ./testdata/
COPY tools/ ./tools/
COPY docker-entrypoint.sh run.sh ./
RUN chmod +x docker-entrypoint.sh run.sh

# Ensure data directory exists for volumes
RUN mkdir -p data

EXPOSE 8000

ENV PYTHONUNBUFFERED=1
ENV PORT=8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD python tools/healthcheck.py || exit 1

ENTRYPOINT ["./docker-entrypoint.sh"]
