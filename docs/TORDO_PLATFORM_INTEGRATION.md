# Integracion con Tordo Platform

RCN debe integrarse como servicio satelite detras de Kong, siguiendo el mismo patron de Tecolyt.

## Rutas esperadas

```text
/rcn/api/* -> RCN FastAPI /api/*
/rcn/ui/*  -> RCN Angular
```

## Variables de entorno

Agregar al environment activo de `/opt/tordo-platform/environments/*.env`:

```bash
# --- Remote Career Navigator (activar agregando 'rcn' a COMPOSE_PROFILES) ---
RCN_TAG=main
RCN_PORT=8050
RCN_UI_PREFIX=/rcn/ui
```

Tambien agregar `rcn` a `COMPOSE_PROFILES`.

## Servicio Docker Compose

Agregar en `/opt/tordo-platform/compose/docker-compose.base.yml`:

```yaml
  rcn:
    image: ${IMAGE_REGISTRY:-ghcr.io}/${IMAGE_OWNER:-htm4rck}/remote-career-navigator:${RCN_TAG:-main}
    restart: unless-stopped
    profiles: ["rcn"]
    environment:
      PORT: ${RCN_PORT:-8050}
      RCN_APP_NAME: Remote Career Navigator API
      RCN_APP_VERSION: 0.1.0
      RCN_DATABASE_URL: postgresql+psycopg://${DB_USER:-postgres}:${DB_PASSWORD:?DB_PASSWORD is required}@postgres:5432/${DB_NAME:-tordo}
      RCN_CORS_ORIGINS: '["*"]'
      RCN_STATIC_FILES_DIR: /app/public
      RCN_UI_PREFIX: ${RCN_UI_PREFIX:-/rcn/ui}
    depends_on:
      postgres:
        condition: service_healthy
    networks:
      tordo_network:
        aliases:
          - rcn
```

## Kong

Agregar upstream en `/opt/tordo-platform/kong/kong.prod.yml`, y repetir en `kong.dev.yml` o `kong.lab.yml` si aplica:

```yaml
  # --- Remote Career Navigator ---
  - name: rcn-upstream
    healthchecks:
      active: { http_path: /api/health, healthy: { interval: 5, successes: 1, http_statuses: [200,301,302,400,401,403,404,500] }, unhealthy: { interval: 5, tcp_failures: 2, timeouts: 2, http_failures: 0 } }
    targets:
      - { target: "rcn:8050", weight: 1000 }
```

Agregar servicios:

```yaml
  # --- Remote Career Navigator ---
  - name: rcn-api-service
    host: rcn-upstream
    path: /api
    routes: [{ name: rcn-api-route, paths: [/rcn/api], strip_path: true, protocols: [http, https] }]

  - name: rcn-ui-service
    host: rcn-upstream
    routes: [{ name: rcn-ui-route, paths: [/rcn/ui], strip_path: false, protocols: [http, https] }]
```

## Build de imagen

Para que Angular compile con el prefijo correcto:

```bash
docker build --build-arg UI_PREFIX=/rcn/ui/ -t ghcr.io/htm4rck/remote-career-navigator:main .
```
