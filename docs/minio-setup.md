# S3 object storage setup

The Endpoint can manage buckets and objects in any S3-compatible service. With
`S3_ENABLED=True` it mounts the `/s3/buckets/…` and `/s3/objects/…` routes and
shows the **S3 Management** tool in the UI. Every one of those routes —
listing and downloading included — requires the **writer** role (see
[roles-and-permissions.md](roles-and-permissions.md)).

There are two ways to provide the storage:

1. [The bundled service](#1-the-bundled-service-compose-profile-s3) — started
   next to the Endpoint by Docker Compose. Intended for development and small
   installations.
2. [An S3 service you already run](#2-an-s3-service-you-already-run) — MinIO,
   Amazon S3 or any other S3-compatible service.

`POST /s3` is a different feature: it registers a **catalog dataset** that
points at an S3 URL, and is controlled by `CKAN_LOCAL_ENABLED`, not by
`S3_ENABLED`.

---

## 1. The bundled service (Compose profile `s3`)

`docker-compose.yml` defines a `minio` service behind the `s3` profile. It runs
`pgsty/silo` (pinned to `RELEASE.2026-09-16T00-00-00Z`), a community fork of
MinIO: the `minio/minio` images were removed from Docker Hub in September 2026
and Silo keeps the S3 API, the `MINIO_*` variables and the server command.

| | Value |
|---|---|
| Container | `ndp-minio` |
| S3 API | `minio:9000` inside the Compose network; `http://localhost:9002` on the host |
| Web console | `http://localhost:9003` on the host (container port 9001) |
| Credentials | `minioadmin` / `minioadmin123` (development defaults, set in `docker-compose.yml`) |
| Data | Docker volume `minio_data` |

### With the installer

Answer yes to **"Enable S3 object storage?"** and choose **"MinIO, installed
alongside the Endpoint"** (or pass `--s3`). The installer adds the `s3` profile
and writes:

```env
S3_ENABLED=True
S3_ENDPOINT=minio:9000
S3_ACCESS_KEY=minioadmin
S3_SECRET_KEY=minioadmin123
S3_SECURE=False
S3_REGION=us-east-1
```

See [installing-with-the-script.md](installing-with-the-script.md#s3-object-storage).

### By hand

Set the same values in `.env` and start the Endpoint with the profile:

```bash
docker compose --profile s3 up -d
```

The Endpoint reaches the service by its Compose name, so `S3_ENDPOINT` is
`minio:9000` (the container port), not `localhost:9002`.

To change the credentials, change `MINIO_ROOT_USER` / `MINIO_ROOT_PASSWORD` in
`docker-compose.yml` and `S3_ACCESS_KEY` / `S3_SECRET_KEY` in `.env` together.

---

## 2. An S3 service you already run

Point the Endpoint at it in `.env`:

```env
S3_ENABLED=True
# host:port, no scheme, reachable from inside the Endpoint container
S3_ENDPOINT=s3.example.org:9000
S3_ACCESS_KEY=<access key>
S3_SECRET_KEY=<secret key>
# True when the service is served over https
S3_SECURE=True
S3_REGION=us-east-1
```

For Amazon S3, `S3_ENDPOINT=s3.amazonaws.com` with `S3_SECURE=True` and the
bucket region. A service on the Docker host itself is reachable from the
container as `host.docker.internal:<port>` (the `api` service maps that name to
the host gateway).

With the installer: answer yes to **"Enable S3 object storage?"**, choose **"An
S3-compatible service I already have"** and give the endpoint, keys, region and
whether to use https — or pass `--s3-endpoint`, `--s3-access-key`,
`--s3-secret-key`, `--s3-region` and `--s3-secure`.

The client is the `minio` Python package
([`api/services/minio_services/minio_client.py`](../api/services/minio_services/minio_client.py)),
created with `S3_ENDPOINT`, the two keys, `S3_SECURE` and `S3_REGION`.

---

## 3. Verify

Restart the Endpoint after changing `.env`. Then:

```bash
# Readiness: "minio" should be "up"
curl -s http://localhost:8002/ready

# The S3 connection as the UI sees it ("s3_enabled", "s3_connected")
curl -s http://localhost:8002/status/ -H "Authorization: Bearer $TOKEN"

# List buckets (writer role required)
curl -s http://localhost:8002/s3/buckets/ -H "Authorization: Bearer $TOKEN"

# Create a bucket
curl -s -X POST http://localhost:8002/s3/buckets/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name": "test-bucket"}'
```

`8002` is the default host port (`EP_API_PORT`); prefix the paths with
`ROOT_PATH` if one is set. The bucket routes are declared with a trailing
slash: `/s3/buckets` without it answers with a 307 redirect to `/s3/buckets/`.
The startup log of each worker also says whether the S3 connection succeeded
(`S3 connection successful` or `S3 connection failed`).

The full set of S3 routes is in
[api-usage-guide.md](api-usage-guide.md#s3-buckets-and-objects).

---

## Troubleshooting

- **`/ready` reports `minio` down, or every S3 route answers 500** — the
  Endpoint cannot reach `S3_ENDPOINT` from inside its container. `localhost`
  there is the container itself; use `minio:9000` for the bundled service or
  `host.docker.internal:<port>` for one on the host.
- **`503 S3 service is not configured`** — `S3_ENDPOINT`, `S3_ACCESS_KEY` or
  `S3_SECRET_KEY` is empty.
- **`/s3/...` answers 404** — `S3_ENABLED` is not `True`, so the routes are
  not mounted.
- **403** — the caller does not have the writer role, or does not pass the
  group gate when `ENABLE_GROUP_BASED_ACCESS=True`.
- **Signature or TLS errors** — check `S3_SECURE` against the service's scheme
  and `S3_REGION` against the bucket region.
- **The `ndp-minio` container does not start** — check that host ports 9002
  and 9003 are free, and `docker logs ndp-minio`.
