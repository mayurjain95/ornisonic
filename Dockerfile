# Backend image (FastAPI + BirdNET). The frontend is deployed separately.
FROM python:3.11-slim

# ffmpeg: audioread/pydub need it to decode mp3 and other compressed formats.
RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg \
    && rm -rf /var/lib/apt/lists/*

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    TF_CPP_MIN_LOG_LEVEL=2 \
    MPLCONFIGDIR=/tmp/matplotlib

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/ backend/
COPY watchlist/ watchlist/
COPY scripts/ scripts/

RUN useradd --create-home app
USER app

# Cloud Run sets PORT (8080 by default). Secrets and DATABASE_URL come from
# the runtime environment, never from a baked-in .env.
ENV PORT=8080
EXPOSE 8080
CMD ["sh", "-c", "exec uvicorn backend.main:app --host 0.0.0.0 --port ${PORT}"]
