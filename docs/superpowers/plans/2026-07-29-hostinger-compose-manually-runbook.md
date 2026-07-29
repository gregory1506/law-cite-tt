# Hostinger "Compose Manually" Runbook

This is the click-by-click and command-by-command production deployment
procedure for LawCite TT.

It uses:

- Hostinger VPS Docker Manager
- Hostinger's standalone Traefik project
- Docker Manager's **Compose manually** YAML editor
- PostgreSQL 16 with pgvector on the VPS
- A prebuilt LawCite FastAPI image loaded onto the VPS
- The existing Cloudflare Worker frontend

The frontend remains at:

```text
https://law-cite-tt.gjo-ai.workers.dev
```

The API will be:

```text
https://srv1629323.hstgr.cloud
```

## Important Constraints

1. Do not paste the repository's current Compose file into Hostinger yet.
2. Do not add PostgreSQL `ports:`. PostgreSQL must not be internet-accessible.
3. Do not deploy the API before the database restore passes its count checks.
4. Do not use `build:` in Hostinger's manual Compose. The manual project does
   not contain this repository or its Dockerfile.
5. Do not use the `data/init.sql` bind mount in Hostinger. The full PostgreSQL
   dump restores the extension, tables, indexes, and data.
6. Do not deploy a second Traefik project if Hostinger Traefik is already
   running.
7. Do not delete the LawCite Docker Manager project after it contains data.
   Use **Update**. The named database volume must survive container recreation.

## Values To Prepare

Record these before starting:

| Name | Value |
|---|---|
| Hostinger project name | `lawcite` |
| Database container | `lawcite-db` |
| API container | `lawcite-api` |
| Database name | `lawcite` |
| Database user | `lawcite` |
| API domain | `srv1629323.hstgr.cloud` |
| Traefik network | `traefik-proxy` |
| Expected chapters | `533` |
| Expected versions | `4989` |
| Expected chunks | `407008` |
| Expected embeddings | `407008` |

Generate one database password locally:

```bash
openssl rand -hex 32
```

Save it in a password manager. The exact same 64-character value must replace
every `REPLACE_WITH_DATABASE_PASSWORD` marker below.

Hex is required here because the API password is embedded in a PostgreSQL URL.
Punctuation in a random password would require URL encoding.

## Step 1: Confirm The VPS Architecture And Capacity

In hPanel:

1. Open **VPS**.
2. Select the VPS and click **Manage**.
3. Open **Docker Manager**.
4. Click **Browser terminal**.

Run:

```bash
uname -m
free -h
df -h /
docker version
docker compose version
docker ps
docker network ls
```

Expected:

- `uname -m` is normally `x86_64`.
- At least 8 GB total RAM is preferred.
- At least 15 GB free disk is available.
- Docker Engine and Docker Compose v2 respond successfully.

Stop if the VPS has less than 4 GB RAM or less than 10 GB free disk. Do not
guess at the image architecture; use the `uname -m` result in Step 4.

## Step 2: Confirm Hostinger Traefik

Hostinger Docker Manager uses a separate Traefik project to own ports 80 and
443 and route other Compose projects by labels.

In **Docker Manager → Projects**:

1. Look for an existing Traefik project.
2. Expand it and confirm the Traefik container is running.
3. Open its logs and confirm there is no certificate or Docker-provider error.

In **Browser terminal**, run:

```bash
docker network inspect traefik-proxy
```

Expected: JSON describing an existing Docker bridge network.

If the network does not exist:

1. Return to **Docker Manager**.
2. Open the Docker application catalog.
3. Locate Hostinger's Traefik template.
4. Deploy it once.
5. Wait until its container is running.
6. Run `docker network inspect traefik-proxy` again.

Do not continue until `traefik-proxy` exists. Only Traefik should publish host
ports 80 and 443.

## Step 3: Confirm DNS

From the local computer:

```bash
dig +short srv1629323.hstgr.cloud
```

The result must be the public IP of this Hostinger VPS.

Also confirm ports 80 and 443 are allowed in the Hostinger firewall. Do not
open port 5432.

## Step 4: Prepare The API Image Locally

Hostinger **Compose manually** can pull or use an image, but it cannot build
this private repository without a build context. This runbook transfers the
image directly, avoiding a public image registry.

Before building:

1. Commit the production CORS change in `backend/api/main.py`.
2. Add and verify `.dockerignore`.
3. Run the backend tests.
4. Ensure `git status` contains no unintended source changes.

From the repository root:

```bash
pytest
git rev-parse --short HEAD
```

Use the returned Git SHA as `IMAGE_TAG`:

```bash
IMAGE_TAG=<git-short-sha>
```

If the VPS reported `x86_64`:

```bash
docker buildx build \
  --platform linux/amd64 \
  --load \
  -f backend/Dockerfile \
  -t "lawcite-api:${IMAGE_TAG}" \
  .
```

If the VPS reported `aarch64`, use `--platform linux/arm64` instead.

Smoke-test the image exists:

```bash
docker image inspect "lawcite-api:${IMAGE_TAG}"
```

Export and checksum it:

```bash
docker save "lawcite-api:${IMAGE_TAG}" \
  | gzip \
  > "/tmp/lawcite-api-${IMAGE_TAG}.tar.gz"

shasum -a 256 "/tmp/lawcite-api-${IMAGE_TAG}.tar.gz" \
  > "/tmp/lawcite-api-${IMAGE_TAG}.tar.gz.sha256"
```

## Step 5: Export The Validated Local PostgreSQL Database

Start the local PostgreSQL container if needed:

```bash
docker compose up -d db
docker compose ps db
```

Confirm the local source counts before dumping:

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

Required result:

```text
533 | 4989 | 407008 | 407008
```

Stop if these counts differ.

Create a full custom-format dump:

```bash
docker compose exec -T db \
  pg_dump \
  -U lawcite \
  -d lawcite \
  -Fc \
  --no-owner \
  --no-acl \
  > /tmp/lawcite-pre-vps.dump

test -s /tmp/lawcite-pre-vps.dump

shasum -a 256 /tmp/lawcite-pre-vps.dump \
  > /tmp/lawcite-pre-vps.dump.sha256
```

## Step 6: Upload The Image And Database Dump

In the Hostinger **Browser terminal**:

```bash
mkdir -p /root/lawcite-import
chmod 700 /root/lawcite-import
```

From the local computer, replace `<VPS_IP>` and `<IMAGE_TAG>`:

```bash
scp \
  "/tmp/lawcite-api-<IMAGE_TAG>.tar.gz" \
  "/tmp/lawcite-api-<IMAGE_TAG>.tar.gz.sha256" \
  "/tmp/lawcite-pre-vps.dump" \
  "/tmp/lawcite-pre-vps.dump.sha256" \
  "root@<VPS_IP>:/root/lawcite-import/"
```

Back in the Hostinger **Browser terminal**:

```bash
cd /root/lawcite-import
sha256sum -c "lawcite-api-<IMAGE_TAG>.tar.gz.sha256"
sha256sum -c lawcite-pre-vps.dump.sha256
```

Both checks must say `OK`.

Load the API image:

```bash
gunzip -c "lawcite-api-<IMAGE_TAG>.tar.gz" | docker load
docker image inspect "lawcite-api:<IMAGE_TAG>"
```

Do not delete the uploaded files yet.

## Step 7: Create The Database-Only Project

In hPanel:

1. Open **VPS → Manage → Docker Manager → Projects**.
2. Click **Compose**.
3. Select **Compose manually**.
4. Set **Project name** to `lawcite`.
5. Select the YAML editor.
6. Paste the Stage A Compose below.
7. Replace `REPLACE_WITH_DATABASE_PASSWORD` with the saved 64-character
   password.
8. Review the right-side preview.
9. Click **Deploy**.

### Stage A Compose: PostgreSQL Only

```yaml
services:
  db:
    image: pgvector/pgvector:0.8.2-pg16-bookworm
    container_name: lawcite-db
    restart: unless-stopped
    shm_size: 256mb
    cpus: "2.0"
    mem_limit: 3g
    environment:
      POSTGRES_DB: lawcite
      POSTGRES_USER: lawcite
      POSTGRES_PASSWORD: "REPLACE_WITH_DATABASE_PASSWORD"
    volumes:
      - pgdata:/var/lib/postgresql/data
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

volumes:
  pgdata:
    name: lawcite_pgdata

networks:
  backend:
    name: lawcite_backend
    internal: true
```

Expected after deployment:

- Project `lawcite` is visible.
- Container `lawcite-db` is running and becomes healthy.
- No host ports are shown for PostgreSQL.
- Volume `lawcite_pgdata` exists.

Confirm in **Browser terminal**:

```bash
docker ps --filter name=lawcite-db
docker inspect lawcite-db --format '{{json .State.Health}}'
docker volume inspect lawcite_pgdata
docker port lawcite-db
```

`docker port lawcite-db` should print nothing.

## Step 8: Restore The Database

Copy the dump into the database container:

```bash
docker cp \
  /root/lawcite-import/lawcite-pre-vps.dump \
  lawcite-db:/tmp/lawcite-pre-vps.dump
```

List the dump before restoring:

```bash
docker exec lawcite-db \
  pg_restore -l /tmp/lawcite-pre-vps.dump
```

Restore using two parallel jobs:

```bash
docker exec lawcite-db \
  pg_restore \
  -U lawcite \
  -d lawcite \
  --clean \
  --if-exists \
  --no-owner \
  --no-acl \
  --exit-on-error \
  --jobs=2 \
  /tmp/lawcite-pre-vps.dump
```

Refresh planner statistics:

```bash
docker exec lawcite-db \
  psql -U lawcite -d lawcite -v ON_ERROR_STOP=1 -c \
  "ANALYZE chapters; ANALYZE versions; ANALYZE chunks;"
```

Verify exact counts:

```bash
docker exec lawcite-db \
  psql -U lawcite -d lawcite -v ON_ERROR_STOP=1 -c "
    SELECT
      (SELECT count(*) FROM chapters) AS chapters,
      (SELECT count(*) FROM versions) AS versions,
      (SELECT count(*) FROM chunks) AS chunks,
      (SELECT count(*) FROM chunks WHERE embedding IS NOT NULL) AS embedded;
  "
```

Required:

```text
533 | 4989 | 407008 | 407008
```

Check the extension and vector dimension:

```bash
docker exec lawcite-db \
  psql -U lawcite -d lawcite -v ON_ERROR_STOP=1 -c \
  "SELECT extversion FROM pg_extension WHERE extname = 'vector';"

docker exec lawcite-db \
  psql -U lawcite -d lawcite -v ON_ERROR_STOP=1 -c \
  "SELECT vector_dims(embedding) FROM chunks WHERE embedding IS NOT NULL LIMIT 1;"
```

The vector dimension must be `384`.

Stop here if any verification fails. Do not add the API.

## Step 9: Update The Hostinger Project To Add The API

In **Docker Manager → Projects**:

1. Find project `lawcite`.
2. Open the **Options (⋮)** menu.
3. Click **Update**.
4. Open the YAML editor.
5. Replace the Stage A YAML with the complete Stage B Compose below.
6. Replace both `REPLACE_WITH_DATABASE_PASSWORD` values with the exact same
   password used in Stage A.
7. Replace `REPLACE_WITH_IMAGE_TAG` with the tag loaded in Step 6.
8. Review the preview carefully.
9. Click **Update/Deploy**.

Do not change the volume name `lawcite_pgdata`. Docker Manager may recreate
the database container, but it must reattach the existing named volume.

### Stage B Compose: PostgreSQL + API + Traefik

```yaml
services:
  db:
    image: pgvector/pgvector:0.8.2-pg16-bookworm
    container_name: lawcite-db
    restart: unless-stopped
    shm_size: 256mb
    cpus: "2.0"
    mem_limit: 3g
    environment:
      POSTGRES_DB: lawcite
      POSTGRES_USER: lawcite
      POSTGRES_PASSWORD: "REPLACE_WITH_DATABASE_PASSWORD"
    volumes:
      - pgdata:/var/lib/postgresql/data
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
    image: lawcite-api:REPLACE_WITH_IMAGE_TAG
    pull_policy: never
    container_name: lawcite-api
    restart: unless-stopped
    init: true
    cpus: "1.5"
    mem_limit: 2g
    depends_on:
      db:
        condition: service_healthy
    environment:
      PG_DSN: "postgresql://lawcite:REPLACE_WITH_DATABASE_PASSWORD@db:5432/lawcite"
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
      - traefik-proxy
    labels:
      - traefik.enable=true
      - traefik.docker.network=traefik-proxy
      - traefik.http.routers.lawcite-api.rule=Host(`srv1629323.hstgr.cloud`)
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
  traefik-proxy:
    external: true
    name: traefik-proxy
```

The first API start can take several minutes while FastEmbed downloads
`sentence-transformers/all-MiniLM-L6-v2` into `lawcite_model_cache`.

## Step 10: Verify Containers In Hostinger

In **Docker Manager → Projects → lawcite**:

1. Confirm both containers show as running.
2. Open `lawcite-db` logs and check for database errors.
3. Open `lawcite-api` logs.
4. Wait for the FastEmbed model download and Uvicorn startup.
5. Confirm `lawcite-api` becomes healthy.

In **Browser terminal**:

```bash
docker ps --filter name=lawcite
docker inspect lawcite-db --format '{{.State.Health.Status}}'
docker inspect lawcite-api --format '{{.State.Health.Status}}'
docker logs --tail=200 lawcite-api
```

Verify the API internally:

```bash
docker exec lawcite-api python -c \
  'import urllib.request; print(urllib.request.urlopen("http://127.0.0.1:8000/api/health").read().decode())'
```

Expected:

```json
{"status":"ok"}
```

If the model download fails, do not repeatedly recreate the project. Read the
API logs, confirm outbound DNS/network access, and retry the API container
after correcting the network problem.

## Step 11: Verify Traefik And HTTPS

Check Traefik logs in Hostinger Docker Manager. It should discover the
`lawcite-api` router without needing a Traefik restart.

From the local computer:

```bash
curl -fsS https://srv1629323.hstgr.cloud/api/health
curl -fsS https://srv1629323.hstgr.cloud/api/stats
```

Expected stats:

```json
{
  "chapters": 533,
  "versions": 4989,
  "chunks": 407008,
  "embedded": 407008
}
```

Verify FTS:

```bash
curl -fsS \
  'https://srv1629323.hstgr.cloud/api/search?q=absconding%20debtor&mode=fts&limit=1'
```

Verify vector search:

```bash
curl -fsS \
  'https://srv1629323.hstgr.cloud/api/search?q=absconding%20debtor&mode=vector&limit=1'
```

Both must return a non-empty JSON array.

## Step 12: Verify CORS

Run:

```bash
curl -i \
  -H 'Origin: https://law-cite-tt.gjo-ai.workers.dev' \
  https://srv1629323.hstgr.cloud/api/health
```

Required response header:

```text
access-control-allow-origin: https://law-cite-tt.gjo-ai.workers.dev
```

If that header is missing, the API image was built without the production
CORS change. Rebuild and load a new image tag; do not weaken CORS to `*`.

## Step 13: Verify The Live Frontend

Open:

```text
https://law-cite-tt.gjo-ai.workers.dev
```

After the stub sign-in:

1. Confirm all four stats contain real numbers.
2. Search `absconding debtor` using full-text mode.
3. Repeat using vector mode.
4. Open Section Lookup and query chapter `8:08`, section `24(1)`.
5. Open Browse Chapters and confirm the list loads.
6. Repeat at a mobile viewport.
7. Confirm the browser console contains no CORS or fetch errors.

The deployment is not complete until these flows use the real VPS data.

## Step 14: Create The First VPS Backup

In Hostinger **Browser terminal**:

```bash
mkdir -p /root/lawcite-backups
chmod 700 /root/lawcite-backups

docker exec lawcite-db \
  pg_dump -U lawcite -d lawcite -Fc --no-owner --no-acl \
  > "/root/lawcite-backups/lawcite-$(date +%F-%H%M).dump"

sha256sum /root/lawcite-backups/lawcite-*.dump \
  > /root/lawcite-backups/SHA256SUMS
```

Download or copy this backup off the VPS. A backup stored only on the same VPS
is not sufficient.

Schedule daily backups after the first deployment and retain at least:

- 7 daily dumps
- 4 weekly dumps
- 1 off-VPS copy

## Step 15: Clean Up Import Files

Only after:

- exact database counts pass,
- live FTS and vector searches pass,
- the frontend works, and
- the first VPS backup exists off-host,

remove the temporary dump copy from inside the database container:

```bash
docker exec lawcite-db rm -f /tmp/lawcite-pre-vps.dump
```

Keep `/root/lawcite-import/` until the deployment has remained stable for at
least 24 hours.

## Updating The API Later

For every API release:

1. Run tests locally.
2. Build a new image with a new Git SHA tag.
3. Export, checksum, and upload it.
4. Load it using `docker load`.
5. Open **Docker Manager → Projects → lawcite → Options → Update**.
6. Change only `api.image` to the new tag.
7. Keep the database password and volume names unchanged.
8. Click **Update**.
9. Re-run health, CORS, FTS, vector, and frontend checks.

Keep the previous image tag on the VPS until the new release is verified.
Rollback means editing `api.image` back to the prior tag and clicking Update.

## Troubleshooting

### Hostinger deployment validation fails

Open **Browser terminal** and inspect:

```bash
cat /docker/lawcite/.build.log
```

Hostinger documents project build logs under `/docker/[project-name]/.build.log`.

### `network traefik-proxy declared as external, but could not be found`

Hostinger Traefik is not installed or its shared network has a different name.
Run `docker network ls` and inspect the Traefik project. Update both the
network declaration and `traefik.docker.network` label to the actual name.

### Traefik returns 502

Check:

```bash
docker inspect lawcite-api --format '{{json .NetworkSettings.Networks}}'
docker inspect <traefik-container> --format '{{json .NetworkSettings.Networks}}'
```

Both containers must be on `traefik-proxy`, and the API must listen on
`0.0.0.0:8000`.

### API is unhealthy

Check:

```bash
docker logs --tail=300 lawcite-api
docker inspect lawcite-api --format '{{json .State.Health}}'
```

Likely causes:

- FastEmbed model download still running or failed
- wrong database password in the API DSN
- PostgreSQL restore incomplete
- container memory exhaustion

### PostgreSQL password authentication fails after an update

Changing `POSTGRES_PASSWORD` does not change the password inside an existing
PostgreSQL volume. Restore the exact original value in both Compose locations.

### Frontend says `Failed to fetch`

Test in order:

1. `/api/health` through HTTPS
2. Traefik logs
3. API container health
4. CORS response header
5. browser console

Do not assume the database is the problem until the HTTPS and CORS checks pass.

## Hostinger References

- Docker Manager overview and Compose manually:
  https://www.hostinger.com/support/12040789-hostinger-docker-manager-for-vps-simplify-your-container-deployments/
- Compose manually deployment flow:
  https://www.hostinger.com/support/12040815-how-to-deploy-your-first-container-with-hostinger-docker-manager/
- Connecting separate Compose projects through Hostinger Traefik:
  https://www.hostinger.com/support/connecting-multiple-docker-compose-projects-using-traefik-in-hostinger-docker-manager/
- Managing, updating, and viewing Docker Manager projects:
  https://www.hostinger.com/support/hostinger-vps-how-to-manage-your-docker-projects/
- Docker Manager troubleshooting and build logs:
  https://www.hostinger.com/support/12040867-troubleshooting-common-docker-manager-issues/
