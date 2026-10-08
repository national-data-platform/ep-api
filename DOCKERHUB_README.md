# NDP Endpoint API

`rbardaji/ndp-ep-api` is the NDP Endpoint: the service an institution runs to
take part in the [National Data Platform](https://nationaldataplatform.org).
One image contains the FastAPI backend and the React web UI, behind nginx.

Source, documentation and issues:
https://github.com/national-data-platform/ep-api

## Run

```bash
docker run -p 8002:80 --env-file .env rbardaji/ndp-ep-api
```

nginx listens on port 80 inside the container. With the command above:

- Web UI: http://localhost:8002/ui/
- API documentation: http://localhost:8002/docs
- Liveness: http://localhost:8002/health

With `ROOT_PATH` set (e.g. `/ep`), everything moves under it: the UI at
`/ep/ui/`, the API at `/ep/` and `/ep/api/`.

## Configure

Start from `example.env` in the repository and see
[docs/configuration.md](https://github.com/national-data-platform/ep-api/blob/main/docs/configuration.md)
for every variable. `TEST_TOKEN` defaults to `testing_token`, which is
accepted as an administrator token: set it empty in production.

For the optional services (MongoDB, S3 storage, Kafka, JupyterLab, Pelican)
and the installer, see the
[README](https://github.com/national-data-platform/ep-api#readme).

## Tags

`X.Y.Z` for each release, and `latest` for the newest non-prerelease. Images
are built for `linux/amd64`.
