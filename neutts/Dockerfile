FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    HF_HOME=/data/huggingface

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        build-essential \
        cmake \
        libgomp1 \
        libopenblas-dev \
        libsndfile1 \
    && rm -rf /var/lib/apt/lists/* \
    && pip install --index-url https://download.pytorch.org/whl/cpu \
        "torch==2.8.0" \
        "torchaudio==2.8.0" \
    && CMAKE_ARGS="-DGGML_BLAS=ON -DGGML_BLAS_VENDOR=OpenBLAS" pip install \
    "fastapi==0.115.12" \
    "uvicorn[standard]==0.34.0" \
    "neutts[all]==1.4.1"

COPY app.py /app/app.py

EXPOSE 8055

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8055", "--workers", "1"]
