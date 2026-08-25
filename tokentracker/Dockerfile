FROM node:20-alpine

# tokentracker-cli has no official Docker image (source: local CLI + native
# desktop apps only). Its `tracker serve` command hardcodes a 127.0.0.1 bind
# with no --host flag or env override (src/commands/serve.js, LOCAL_BIND_HOST),
# so it cannot be published from a container as-is. socat forwards the
# container's external interface to that loopback-only server.
RUN apk add --no-cache socat su-exec \
  && npm install -g tokentracker-cli \
  && addgroup -S tokentracker \
  && adduser -S tokentracker -G tokentracker -h /home/tokentracker

ENV HOME=/home/tokentracker \
  TOKENTRACKER_PORT=7680

COPY entrypoint.sh /usr/local/bin/entrypoint.sh
COPY run-tracker.sh /usr/local/bin/run-tracker.sh
RUN chmod +x /usr/local/bin/entrypoint.sh /usr/local/bin/run-tracker.sh \
  && chown -R tokentracker:tokentracker /home/tokentracker

WORKDIR /home/tokentracker
# Stay root at container start: entrypoint.sh chowns the bind-mounted data
# volume (which arrives owned by the host UID) before dropping to the
# tokentracker user via su-exec.

EXPOSE 7680

HEALTHCHECK --interval=30s --timeout=5s --retries=3 --start-period=30s \
  CMD node -e "fetch('http://127.0.0.1:${TOKENTRACKER_PORT}/').then(r=>process.exit(r.ok?0:1)).catch(()=>process.exit(1))"

ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
