# LawCite TT VPS Backend + PostgreSQL Deployment Plan

> **Hostinger implementation runbook:** For the exact hPanel **Compose
> manually** workflow, use
> `docs/superpowers/plans/2026-07-29-hostinger-compose-manually-runbook.md`.
> The Hostinger workflow uses a prebuilt API image and a two-stage database
> restore because the manual editor does not provide this repository as a
> Docker build context.

**Goal:** Deploy the FastAPI backend and the existing 407,008-chunk
PostgreSQL/pgvector dataset to the VPS, expose the API through the VPS's
existing Traefik instance at `https://srv1629323.hstgr.cloud`, and connect the
already-deployed Cloudflare Worker frontend.

**Target architecture:**

```text
Browser
  |
  +-- https://law-cite-tt.gjo-ai.workers.dev
  |     Cloudflare Worker static assets (already deployed)
  |
  +-- https://srv1629323.hstgr.cloud/api/*
        |
        Traefik on VPS (existing)
        |
        lawcite-api:8000
        |
        private Docker network
        |
        PostgreSQL 16 + pgvector
```

PostgreSQL has no published host port. Traefik and the API share the existing
external proxy network. The API and PostgreSQL share a private internal
network. The frontend is not deployed on the VPS.

## Assumptions To Confirm

- The VPS has at least 4 vCPU, 8 GB RAM, and 15 GB free disk. A 4 GB VPS may
  work, but gives little headroom for PostgreSQL, the vector index, the
  embedding model, Docker, Traefik, and the operating system.
- Docker Engine and Docker Compose v2 are installed.
- Traefik is already running with Docker discovery, an HTTPS entrypoint named
  `websecure`, and a certificate resolver named `letsencrypt`.
- `srv1629323.hstgr.cloud` resolves to the VPS and ports 80/443 reach Traefik.
- The external Docker network shared by Traefik is known. The Compose file
  below calls it `${TRAEFIK_NETWORK}`.
- The local PostgreSQL database still contains the validated counts:
  `chapters=533`, `versions=4989`, `chunks=407008`, `embedded=407008`.

Do not deploy until the Traefik network, entrypoint, resolver, DNS, VPS memory,
and free disk have been verified.

## Target `docker-compose.yml`

This is the intended production shape. It replaces the current file after
preflight validation. The pinned pgvector tag avoids an unexpected PostgreSQL
or extension upgrade.

```yaml
name: lawcite

services:
  db:
    image: pgvector/pgvector:0.8.2-pg16-bookworm
    restart: unless-stopped
    shm_size: 256mb
    cpus: "2.0"
    mem_limit: 3g
    environment:
      POSTGRES_DB: lawcite
      POSTGRES_USER: lawcite
      POSTGRES_PASSWORD: ${PG_PASSWORD:?set PG_PASSWORD in .env}
    volumes:
      - pgdata:/var/lib/postgresql/data
      - ./data/init.sql:/docker-entrypoint-initdb.d/10-init.sql:ro
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U lawcite -d lawcite"]
      interval: 10s
      timeout: 5s
      retries: 12
      start_period: 30s
    networks:
      - backend
    logging:
      driver: json-file
      options:
        max-size: "10m"
        max-file: "5"

  api:
    image: lawcite-api:${APP_VERSION:-current}
    build:
      context: .
      dockerfile: backend/Dockerfile
    restart: unless-stopped
    init: true
    cpus: "1.5"
    mem_limit: 2g
    depends_on:
      db:
        condition: service_healthy
        restart: true
    environment:
      PG_DSN: postgresql://lawcite:${PG_PASSWORD}@db:5432/lawcite
      PYTHONUNBUFFERED: "1"
      PYTHONDONTWRITEBYTECODE: "1"
      FASTEMBED_CACHE_PATH: /models
    volumes:
      - model_cache:/models
    expose:
      - "8000"
    healthcheck:
      test:
        - CMD
        - python
        - -c
        - import urllib.request; urllib.request.urlopen("http://127.0.0.1:8000/api/health", timeout=5)
      interval: 30s
      timeout: 10s
      retries: 5
      start_period: 180s
    networks:
      - backend
      - proxy
    labels:
      - traefik.enable=true
      - traefik.docker.network=${TRAEFIK_NETWORK}
      - traefik.http.routers.lawcite-api.rule=Host(`${API_DOMAIN}`)
      - traefik.http.routers.lawcite-api.entrypoints=websecure
      - traefik.http.routers.lawcite-api.tls=true
      - traefik.http.routers.lawcite-api.tls.certresolver=letsencrypt
      - traefik.http.routers.lawcite-api.service=lawcite-api
      - traefik.http.services.lawcite-api.loadbalancer.server.port=8000
      - traefik.http.services.lawcite-api.loadbalancer.healthcheck.path=/api/health
      - traefik.http.services.lawcite-api.loadbalancer.healthcheck.interval=30s
      - traefik.http.services.lawcite-api.loadbalancer.healthcheck.timeout=10s
    logging:
      driver: json-file
      options:
        max-size: "10m"
        max-file: "5"

volumes:
  pgdata:
    name: lawcite_pgdata
  model_cache:
    name: lawcite_model_cache

networks:
  backend:
    name: lawcite_backend
    internal: true
  proxy:
    external: true
    name: ${TRAEFIK_NETWORK:?set TRAEFIK_NETWORK in .env}
```

### Why this differs from the current Compose file

- Removes the frontend service because it is already hosted on Cloudflare.
- Removes the PostgreSQL host port completely; administration uses
  `docker compose exec` or a temporary SSH tunnel when required.
- Adds an explicit private application network and explicit external Traefik
  network. Labels alone do not connect containers to Traefik.
- Pins pgvector/PostgreSQL instead of using the moving `pg16` tag.
- Gives the volume a stable name so changing the checkout directory does not
  silently create an empty database.
- Adds API/database health checks and waits for PostgreSQL readiness.
- Persists the FastEmbed model cache across API container replacements.
- Rotates Docker JSON logs to prevent an unbounded disk leak.
- Uses service-level CPU/memory constraints for `docker compose up`.

## Required Environment

Create `/opt/lawcite/.env` on the VPS with mode `0600`:

```dotenv
PG_PASSWORD=<64-character URL-safe random value>
API_DOMAIN=srv1629323.hstgr.cloud
TRAEFIK_NETWORK=<actual external Traefik Docker network>
APP_VERSION=<deployed git short SHA>
```

Generate the password with `openssl rand -hex 32`. Hex is intentionally used
because the password is interpolated into a PostgreSQL URL and therefore must
not contain unescaped URL punctuation.

Do not put secrets in Traefik labels, Git, shell history, or command-line
arguments.

## Phase 1: Repository Preflight

1. Commit the existing CORS change allowing
   `https://law-cite-tt.gjo-ai.workers.dev`.
2. Add `.dockerignore` so the build context excludes `.git`, `.venv`,
   `citation-tool/node_modules`, `citation-tool/dist`, `.wrangler`, test
   caches, local data, and browser artifacts.
3. Add `backups/` to `.gitignore`; database dumps must never enter Git or the
   Docker build context.
4. Consider prefetching `sentence-transformers/all-MiniLM-L6-v2` in the API
   image. The persisted `/models` volume is the minimum requirement; baking
   the model into the image gives more deterministic startup.
5. Update `.env.example` with `API_DOMAIN`, `TRAEFIK_NETWORK`, and
   `APP_VERSION` placeholders.
6. Replace the current Compose file with the target above.
7. Run:

   ```bash
   docker compose config --quiet
   docker compose build api
   pytest
   ```

8. Start a clean local stack and verify `/api/health`, `/api/stats`, FTS,
   vector, and hybrid search before touching the VPS.

**Gate:** no deploy until the local production-shaped stack passes.

## Phase 2: Inspect And Prepare The VPS

Run read-only discovery first:

```bash
docker version
docker compose version
docker info
free -h
df -h
docker ps
docker network ls
docker inspect <traefik-container>
```

Confirm the external network name, `websecure` entrypoint, `letsencrypt`
resolver, and that Traefik has Docker discovery enabled. Then:

```bash
sudo mkdir -p /opt/lawcite/backups
sudo chown -R "$USER":"$USER" /opt/lawcite
git clone <private-repository-url> /opt/lawcite/repo
cd /opt/lawcite/repo
```

Create `.env`, set mode `0600`, and validate without printing interpolated
secrets into shared logs:

```bash
chmod 600 .env
docker compose config --quiet
docker compose pull db
docker compose build api
```

**Gate:** the images build and Compose resolves the external network.

## Phase 3: Export The Validated Local Database

Preferred path: make a PostgreSQL custom-format dump from the already-validated
local PostgreSQL database. This avoids re-running the 407,008-row SQLite
migration on the VPS.

From the local repository:

```bash
mkdir -p backups
docker compose exec -T db \
  pg_dump -U lawcite -d lawcite -Fc --no-owner --no-acl \
  > backups/lawcite-pre-vps.dump
sha256sum backups/lawcite-pre-vps.dump \
  > backups/lawcite-pre-vps.dump.sha256
```

Verify the dump is non-empty and listable:

```bash
test -s backups/lawcite-pre-vps.dump
docker compose exec -T db pg_restore -l \
  < backups/lawcite-pre-vps.dump | head
```

Transfer the dump and checksum over SSH/SFTP to
`/opt/lawcite/backups/`, then verify the checksum on the VPS.

Fallback: if the local PostgreSQL volume no longer exists, copy the validated
SQLite database to the VPS and run
`backend/scripts/migrate_sqlite_to_pg.py`. Do not use this fallback until its
source file checksum and the expected four counts have been recorded.

## Phase 4: Initialize And Restore PostgreSQL

Start only PostgreSQL:

```bash
docker compose up -d db
docker compose ps
docker compose logs --tail=100 db
```

Restore the full custom dump. `--clean --if-exists` replaces the empty schema
created by `data/init.sql`; `--exit-on-error` prevents a partial success from
being mistaken for a valid restore.

```bash
docker compose exec -T db \
  pg_restore -U lawcite -d lawcite \
  --clean --if-exists --no-owner --no-acl --exit-on-error \
  < /opt/lawcite/backups/lawcite-pre-vps.dump
```

Refresh planner statistics:

```bash
docker compose exec -T db \
  psql -U lawcite -d lawcite -v ON_ERROR_STOP=1 \
  -c "ANALYZE chapters; ANALYZE versions; ANALYZE chunks;"
```

Verify counts:

```bash
docker compose exec -T db \
  psql -U lawcite -d lawcite -v ON_ERROR_STOP=1 -c "
    SELECT
      (SELECT count(*) FROM chapters) AS chapters,
      (SELECT count(*) FROM versions) AS versions,
      (SELECT count(*) FROM chunks) AS chunks,
      (SELECT count(*) FROM chunks WHERE embedding IS NOT NULL) AS embedded;
  "
```

**Gate:** exact result must be `533 / 4989 / 407008 / 407008`. If any count
differs, stop. Do not start the API against an unverified restore.

## Phase 5: Start And Verify The API

```bash
docker compose up -d api
docker compose ps
docker compose logs --tail=200 api
```

The first start may download the FastEmbed model and can take several minutes.
The API's health-check `start_period` accommodates that cold start.

Verify inside the API container:

```bash
docker compose exec -T api python -c \
  'import urllib.request; print(urllib.request.urlopen("http://127.0.0.1:8000/api/health").read().decode())'
```

Verify through Traefik:

```bash
curl -fsS https://srv1629323.hstgr.cloud/api/health
curl -fsS https://srv1629323.hstgr.cloud/api/stats
curl -fsS \
  'https://srv1629323.hstgr.cloud/api/search?q=absconding%20debtor&mode=fts&limit=1'
curl -fsS \
  'https://srv1629323.hstgr.cloud/api/search?q=absconding%20debtor&mode=vector&limit=1'
```

Verify CORS explicitly:

```bash
curl -i \
  -H 'Origin: https://law-cite-tt.gjo-ai.workers.dev' \
  https://srv1629323.hstgr.cloud/api/health
```

The response must include:

```text
access-control-allow-origin: https://law-cite-tt.gjo-ai.workers.dev
```

Finally, test Search, Section Lookup, and Browse Chapters from the live
Cloudflare frontend in desktop and mobile browser widths.

**Gate:** deployment is complete only when the frontend retrieves real stats
and results without browser console errors.

## Phase 6: Backups And Operations

Create a daily logical backup on the VPS:

```bash
cd /opt/lawcite/repo
docker compose exec -T db \
  pg_dump -U lawcite -d lawcite -Fc --no-owner --no-acl \
  > "/opt/lawcite/backups/lawcite-$(date +%F-%H%M).dump"
```

Requirements:

- Run daily using a systemd timer or cron.
- Keep at least 7 daily and 4 weekly dumps.
- Copy backups off the VPS using encrypted object storage or another machine.
- Record SHA-256 checksums.
- Perform a restore drill into a disposable database before considering
  backups reliable.
- Monitor `df -h`, container health, PostgreSQL volume size, API error logs,
  request latency, and backup age.

Useful operational commands:

```bash
docker compose ps
docker compose logs -f --tail=200 api
docker compose logs -f --tail=200 db
docker compose restart api
docker compose exec -T db psql -U lawcite -d lawcite
```

Never run `docker compose down -v` in production. The `-v` flag deletes the
database volume.

## Upgrade And Rollback

For an application-only release:

1. Create a fresh database dump.
2. Pull the intended Git commit.
3. Set `APP_VERSION` in `.env` to that commit's short SHA.
4. Run `docker compose build api`.
5. Run `docker compose up -d --no-deps api`.
6. Verify internal health, external health, CORS, and one FTS/vector request.

If the API release fails, restore the previous Git commit and `APP_VERSION`,
then rebuild/recreate only `api`. Do not restore the database for an
application-only rollback unless the release included a database migration.

For a schema or PostgreSQL/pgvector version change, write a separate migration
plan. Do not change the pinned database image as part of a routine API deploy.

## Definition Of Done

- PostgreSQL is reachable only from the private Docker network.
- The named `lawcite_pgdata` volume contains the exact validated corpus.
- API and database containers are healthy after a VPS reboot.
- Traefik serves a valid HTTPS certificate for the API domain.
- The Cloudflare frontend can use stats, search, lookup, and chapter browsing.
- FTS, vector, and hybrid queries return real results.
- CORS permits the production frontend and local development only.
- A timestamped backup exists off the VPS and a restore drill has succeeded.
- Rollback instructions have been exercised at least once.

## Primary References

- Docker Compose startup ordering and `service_healthy`:
  https://docs.docker.com/compose/how-tos/startup-order/
- Docker volume persistence and backup/restore:
  https://docs.docker.com/engine/storage/volumes/
- Traefik Docker provider and network selection:
  https://doc.traefik.io/traefik/providers/docker/
- Traefik Docker routing labels:
  https://doc.traefik.io/traefik/routing/providers/docker/
- PostgreSQL logical dumps and restores:
  https://www.postgresql.org/docs/current/backup-dump.html
- pgvector Docker tags, indexing, and monitoring:
  https://github.com/pgvector/pgvector
