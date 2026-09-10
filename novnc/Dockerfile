FROM debian:bookworm-slim

ARG DEBIAN_FRONTEND=noninteractive

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
       ca-certificates \
       chromium \
       fluxbox \
       fonts-liberation \
       fonts-noto-color-emoji \
       novnc \
       procps \
       websockify \
       wget \
       x11vnc \
       xvfb \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd --system novnc \
    && useradd --system --gid novnc --create-home --home-dir /home/novnc novnc \
    && mkdir -p /app /data /tmp/.X11-unix \
    && chown -R novnc:novnc /app /data /home/novnc \
    && chmod 1777 /tmp/.X11-unix

COPY entrypoint.sh /app/entrypoint.sh
RUN chmod 0755 /app/entrypoint.sh

ENV DISPLAY=:99 \
    DISPLAY_NUM=99 \
    SCREEN_RESOLUTION=1280x800x24 \
    VNC_PORT=5900 \
    NOVNC_PORT=6080 \
    DATA_DIR=/data \
    ENABLE_VNC=true \
    START_BROWSER=true \
    BROWSER_URL=about:blank

EXPOSE 6080
VOLUME ["/data"]

USER novnc
WORKDIR /home/novnc
ENTRYPOINT ["/app/entrypoint.sh"]
