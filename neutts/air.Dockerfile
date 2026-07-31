FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    HF_HOME=/data/huggingface

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        espeak-ng \
        libgomp1 \
        libopenblas0 \
        libsndfile1 \
    && rm -rf /var/lib/apt/lists/* \
    && pip install --index-url https://download.pytorch.org/whl/cpu \
        "torch==2.8.0" \
        "torchaudio==2.8.0" \
    && pip install \
        "fastapi==0.115.12" \
        "uvicorn[standard]==0.34.0" \
        "python-multipart==0.0.20" \
        "neutts==1.4.1"

COPY air_app.py /app/air_app.py

EXPOSE 8056

CMD ["uvicorn", "air_app:app", "--host", "0.0.0.0", "--port", "8056", "--workers", "1"]
