FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    poppler-utils \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install CPU-only PyTorch first using the official PyTorch CPU wheel index
RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu

# Optimize layer caching: copy requirements and install dependencies before application code
COPY requirements.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend application source code
COPY . /app/

EXPOSE 8000

CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
