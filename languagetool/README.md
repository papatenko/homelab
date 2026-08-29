# LanguageTool

Self-hosted LanguageTool HTTP API for privacy-preserving spelling and grammar checks.

## Upstream

- Image project: https://github.com/Erikvl87/docker-languagetool
- LanguageTool project: https://github.com/languagetool-org/languagetool
- API documentation: https://dev.languagetool.org/public-http-api.html

## Runtime

The service listens on port `8010` and exposes the LanguageTool API under `/v2`.
For browser extensions, configure the custom API server as `<service-url>/v2`.

Optional n-gram datasets can be placed in the persistent `DATA_DIR` mount and
are exposed to LanguageTool at `/ngrams`.

## Portainer variables

- `DATA_DIR`: host path for persistent LanguageTool data
- `JAVA_XMS` and `JAVA_XMX`: Java heap bounds, default `512m` and `2g`

Do not commit real deployment values or secrets. Set stack variables in Portainer.

## Validation

```bash
docker compose -f languagetool/docker-compose.yml config
curl --data 'language=en-US&text=This are a test' http://localhost:8010/v2/check
```

## Reverse proxy

LanguageTool can be placed behind a reverse proxy at a dedicated hostname. Keep
`/v2` available and enable CORS/websocket settings only if required by the client.

## Rollback

Remove the Git-backed Portainer stack while retaining the configured `DATA_DIR`
if rollback is needed. The n-gram data can be reused by a later deployment.
