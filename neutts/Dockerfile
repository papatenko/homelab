FROM pytorch/pytorch:2.6.0-cuda12.6-cudnn9-runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

RUN pip install --no-cache-dir \
    "fastapi==0.115.12" \
    "uvicorn[standard]==0.34.0" \
    "neutts==1.4.1"

COPY app.py /app/app.py

EXPOSE 8055

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8055", "--workers", "1"]
