# modula-edocs-download

NGINX + Flask service that serves individual edoc files out of tar.gz archives stored on a bucket mount, fronted by ModSecurity.

## What it does
- Exposes `GET /download` to fetch a single file from a tar.gz produced by the transfer job; validates `filename` and `tar_path` query params.
- Validates `tar_path` shape and builds an absolute path under `FILES_ROOT`, rejecting requests that don’t match the expected tenant/date layout.
- Opens the tarball on disk, extracts the requested member, and returns it as an attachment; 404s if either the archive or member is missing.
- Secures requests with `X-M-Api-Key` and `X-M-Api-Secret` headers (required at startup) and emits structured logs with request IDs and timing.
- Provides `GET /healthz` for probes; JSON responses are wrapped with a standard envelope while file downloads bypass wrapping.

## Paths and layout
- Bucket mount: `FILES_ROOT` (default `/gcp-bucket`; mount your bucket here).
- Expected tar relative path (`tar_path` query param): `<customer_id>/<yy>/<mm>/<dd>/<branch>/<edoc_type>_<HH-MM>.tar.gz`
  - `customer_id` must match `^(stg|prd)-modula-\\d{5}$`.
  - Example: `stg-modula-12345/23/11/08/123/01_12-30.tar.gz`.
- `filename` must match a member inside the tarball; traversal is not supported.

## Required environment
- `FILES_API_KEY`, `FILES_API_SECRET`: header values clients must send; the entrypoint refuses to start without them.

## Optional environment
- `FILES_ROOT` (default `/gcp-bucket`): mount point where tar archives live.
- `LOG_LEVEL` (default `DEBUG`) and `CUSTOMER_ID` (used for log context only).
- Gunicorn tuning: `API_HOST`, `API_PORT`, `GUNICORN_WORKERS`, `GUNICORN_THREADS`, `GUNICORN_TIMEOUT`, `GUNICORN_KEEPALIVE`, `GUNICORN_MAX_REQUESTS`, `GUNICORN_MAX_REQUESTS_JITTER`, `GUNICORN_EXTRA_ARGS`.

## Local run (Docker)
Use the compose helper to run the full nginx + ModSecurity + Gunicorn stack:
```bash
cd /Users/juan-rodriguez/modula-edocs-download
# Create .env with FILES_API_KEY=... and FILES_API_SECRET=... (and optionally FILES_ROOT, LOG_LEVEL, CUSTOMER_ID)
docker compose -f build/docker-compose.yml up --build
```
What `docker-compose.yml` does:
- Builds the image from `build/Dockerfile` and exposes the service on `http://localhost:8081` (nginx listens on 8080 in the container).
- Mounts your bucket dir to `/gcp-bucket` (defaults to `../modula-edocs-transfer/.local/gcp-bucket`; adjust if your data lives elsewhere) and bind-mounts `../api` for code edits.
- Joins the external `modula_shared_net` bridge network; create it first if missing (`docker network create --subnet 172.30.0.0/16 modula_shared_net`).

Example download request after placing a tarball in the mounted bucket:
```bash
curl -H "X-M-Api-Key: $FILES_API_KEY" \
     -H "X-M-Api-Secret: $FILES_API_SECRET" \
     "http://localhost:8081/download?filename=some-file.xml&tar_path=stg-modula-12345/23/11/08/123/01_12-30.tar.gz" \
     -o some-file.xml
```

## Deployment notes
- Image: build from `build/Dockerfile` (nginx + ModSecurity + Gunicorn running `api/app.py`).
- Expose port `8080`; the app listens on `API_PORT` (default 8000) behind nginx.
- Mount your bucket/edoc tar directory to `FILES_ROOT`.
- Set `FILES_API_KEY` and `FILES_API_SECRET`; optionally set `FILES_ROOT`, `LOG_LEVEL`, `CUSTOMER_ID`, and Gunicorn tunables.
- No database dependency; the service only reads tar.gz files from the mounted path.

## Behavior and constraints
- Invalid `tar_path` formats are rejected with 400 to avoid arbitrary path access.
- 404 if the tar archive or requested member is missing; tar parsing errors raise 500.
- Files are read into memory before being returned (no streaming), so size accordingly.
- JSON responses are wrapped with a standard envelope; file downloads return raw attachments.
- Nginx applies ModSecurity (OWASP CRS) and security headers; only GET/POST are allowed through nginx.

## Development quickstart
- Dependencies: Python 3.11; Docker optional for the full stack.
- Install deps locally: `pip install -r build/requirements.txt`
- Run locally without Docker (from repo root): `export FILES_API_KEY=... FILES_API_SECRET=... && python api/app.py` (serves on 0.0.0.0:8000).

## Testing
- All tests live under `tests/unit` and `tests/integration` with stubs for external deps (Flask, Flask-Smorest, pymongo, etc.).
- Recommended command from the repo root (avoids locked `.coverage` by writing to /tmp):
  ```bash
  FILES_API_KEY= FILES_API_SECRET= \
  COVERAGE_FILE=/tmp/modula-edocs-download.coverage \
  python -m pytest -p no:cacheprovider -p pytest_cov --cov=api tests/unit tests/integration
  COVERAGE_FILE=/tmp/modula-edocs-download.coverage coverage report --include='api/*' --show-missing
  ```
- If you prefer the default `.coverage` file, ensure it is writable (delete it first) and drop the `COVERAGE_FILE` export.

## Entry points
- Container entrypoint: `/app/build/entrypoint.sh` → supervisord → nginx + Gunicorn `app:app`.
- HTTP endpoints: `GET /healthz`, `GET /download?filename=<name>&tar_path=<relative_tar_path>`.
