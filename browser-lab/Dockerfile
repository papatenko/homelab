FROM ghcr.io/m1k1o/neko/google-chrome:3.1.5

# Add a loopback-to-Tailscale CDP proxy while retaining the upstream browser/runtime setup.
RUN apt-get update \
    && apt-get install -y --no-install-recommends socat \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Add CDP flags while retaining the upstream Neko browser/runtime setup.
COPY google-chrome.conf /etc/neko/supervisord/google-chrome.conf
COPY policy.json /etc/opt/chrome/policies/managed/policies.json
