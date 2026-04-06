# ==============================================
# Dockerfile — Ultimate AI Agent
# ==============================================
# Lightweight production image for Render / Railway / any cloud
#
# Build:  docker build -t ultimate-agent .
# Run:    docker run -p 10000:10000 -e OPENAI_API_KEY=sk-xxx ultimate-agent

FROM python:3.11-slim

# System deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python deps first (layer caching)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy project
COPY . .

# Create memory directory
RUN mkdir -p memory/conversations memory/facts

# Environment defaults
ENV HEADLESS_MODE=true
ENV API_HOST=0.0.0.0
ENV API_PORT=10000
ENV PYTHONUNBUFFERED=1

EXPOSE 10000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD python -c "import httpx; r = httpx.get('http://localhost:10000/'); assert r.status_code == 200"

# Start the gateway server
CMD ["python", "gateway.py"]
