FROM python:3.13-slim

RUN pip install --no-cache-dir anki \
    && useradd --system --uid 10001 --home-dir /data anki \
    && install -d -o 10001 -g 10001 /data

USER 10001:10001
ENV SYNC_BASE=/data SYNC_HOST=0.0.0.0 SYNC_PORT=8080
EXPOSE 8080
CMD ["python", "-m", "anki.syncserver"]
