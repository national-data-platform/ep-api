# Automating with Python

Every operation an Endpoint exposes through its web app is also available from
code, either by calling its **HTTP API** directly (interactive docs at
`<endpoint-url>/docs`) or through the
[`ndp-ep`](https://pypi.org/project/ndp-ep/) Python library.

This is the path to take when you have **many** items to register, you want to
**schedule** ingestion, or you want to wire publishing into a CI pipeline or an
ETL job.

The library is a separate project
([github.com/sci-ndp/ndp-ep-py](https://github.com/sci-ndp/ndp-ep-py)). The
names below are those of `ndp-ep` **0.9.0**; check the library's own
documentation for the version you install.

## Install

```bash
pip install ndp-ep
```

The library requires Python 3.8 or later and depends on `requests`,
`urllib3` and `PyJWT`. The Pelican and remote-execution helpers need the
`pelican` and `rexec` extras.

## Connect

Create one client and reuse it for every call. Pass either a bearer token you
already have, or your username and password — not both:

```python
from ndp_ep import APIClient

# Option A — a bearer token (for example the NDP access token from your
# user section on nationaldataplatform.org)
client = APIClient(
    base_url="https://ep.my-institution.edu",
    token="<your-bearer-token>",
)

# Option B — username and password; the client signs in through the
# Endpoint's POST /user/login
client = APIClient(
    base_url="https://ep.my-institution.edu",
    username="<username>",
    password="<password>",
)
```

`base_url` is the Endpoint's API root, `<endpoint-url>` — the address of the
web app **without** the `/ui/`. A URL given without a scheme gets `http://`.
The Endpoint applies the same entry and role checks to calls from code as to
the web app: what your token can do from code is exactly what your account can
do in the browser.

> **`http` vs `https`:** use `https://` only when the Endpoint is served on a
> domain with a valid TLS certificate. An Endpoint reached by a bare IP
> address or `localhost` (for example `http://<host-ip>:8002`) is plain
> `http://`.

## Common operations

The registration methods take a dictionary with the same fields as the web
forms (see the cheat-sheet in [Publishing data](03-publishing-data.md)) and
write to the local catalog by default (`server="local"`).

```python
# Browse organizations and search
client.list_organizations(server="local")
client.search_datasets(["storm radar"], server="global")

# Create an organization and a dataset
client.register_organization({
    "name": "atmospheric-research",
    "title": "Atmospheric Research",
})
client.register_general_dataset({
    "name": "storm-radar-2025",
    "title": "Storm radar reflectivity 2025",
    "owner_org": "atmospheric-research",
    "notes": "Hourly NEXRAD Level-II composites over CONUS.",
    "tags": ["radar", "nexrad", "2025"],
})

# Register a URL resource
client.register_url({
    "resource_name": "radar-jan-2025",
    "resource_title": "Radar reflectivity — January 2025",
    "owner_org": "atmospheric-research",
    "resource_url": "https://data.example.org/radar/2025-01.nc",
    "file_type": "NetCDF",
})

# Register an S3 resource
client.register_s3_link({
    "resource_name": "radar-archive-2025",
    "resource_title": "NEXRAD radar archive, 2025",
    "owner_org": "atmospheric-research",
    "resource_s3": "s3://nexrad-archive/2025/",
})

# Register a Kafka topic
client.register_kafka_topic({
    "dataset_name": "nexrad-live",
    "dataset_title": "NEXRAD radar — live stream",
    "owner_org": "atmospheric-research",
    "kafka_topic": "nexrad.live",
    "kafka_host": "kafka.example.org",
    "kafka_port": 9092,
})
```

`register_service`, the `update_*` and `patch_*` methods, and
`delete_organization` / `delete_resource` follow the same pattern. They need
the writer (or admin) role and an Endpoint with a local catalog; on an
Endpoint without one, the API routes they call do not exist.

The library has no method for **Publish** (sending a dataset to the staging
catalog); call the API directly for that:
`POST <endpoint-url>/dataset/<dataset-id>/publish` with the bearer token.

## S3 storage from code

```python
# Buckets
client.list_buckets()
client.create_bucket("radar-archive-2025")
client.get_bucket_info("radar-archive-2025")
client.delete_bucket("radar-archive-2025")  # the bucket must be empty

# Objects
client.upload_object("radar-archive-2025", "2025-01.nc", open("2025-01.nc", "rb").read())
client.list_objects("radar-archive-2025")
client.get_object_metadata("radar-archive-2025", "2025-01.nc")
client.generate_presigned_download_url("radar-archive-2025", "2025-01.nc")
client.download_object("radar-archive-2025", "2025-01.nc")
client.delete_object("radar-archive-2025", "2025-01.nc")
```

Like the S3 storage page, every S3 call requires the **writer** (or admin)
role and an Endpoint with S3 enabled.

## Typical use cases

- **Bulk import.** Walk a directory tree, create one dataset per top-level
  folder, and register each file inside as a URL or S3 resource.
- **Recurring ingestion.** Run a script on a schedule to register new outputs
  of an instrument or pipeline.
- **CI integration.** Have a CI job register a versioned dataset after a build.
- **ETL bridges.** Read the dataset list from the Endpoint, then process each
  resource.

## Where to find more

- The library on PyPI: <https://pypi.org/project/ndp-ep/>.
- The library source and documentation: <https://github.com/sci-ndp/ndp-ep-py>.
- The Endpoint's interactive HTTP API: `<endpoint-url>/docs`.
