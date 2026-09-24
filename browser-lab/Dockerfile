FROM ghcr.io/m1k1o/neko/google-chrome:3.1.5

# Add CDP flags while retaining the upstream Neko browser/runtime setup.
COPY google-chrome.conf /etc/neko/supervisord/google-chrome.conf
COPY policy.json /etc/opt/chrome/policies/managed/policies.json
