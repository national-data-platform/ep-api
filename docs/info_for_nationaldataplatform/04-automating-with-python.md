# Automating with Python

Every operation an Endpoint exposes through its web app is also available from
code, either by calling its **HTTP API** directly (interactive docs at
`…/ep-api/docs`) or — more conveniently — through the
[`ndp-ep`](https://pypi.org/project/ndp-ep/) Python library.

This is the path to take when you have **many** items to register, you want to
**schedule** ingestion, or you want to wire publishing into a CI pipeline or an
ETL job.

## Install

```bash
pip install ndp-ep
```

The library targets Python 3.10+ and has no native dependencies beyond
`requests`.

## Connect

You authenticate once and reuse the client for all calls. You can either pass a
bearer token you already have, or sign in with username/password:

```python
from ndp_ep import APIClient

# Option A — pass a bearer token (e.g. from your NDP session)
client = APIClient(
    base_url="https://my-endpoint.example.org/ep-api",
    token="<your-bearer-token>",
)

# Option B — sign in with username/password
client = APIClient(base_url="https://my-endpoint.example.org/ep-api")
client.get_token(username="me@my-institution.edu", password="…")
```

`base_url` is the same root the web app uses, **without** the `/ui/`. The
client honours the Endpoint's role checks — what your token can do from code is
exactly what your account can do from the web.

> **`http` vs `https`:** the `https://…` examples above assume the Endpoint is
> served on a real domain with a valid TLS certificate. If you reach it by a
> bare **IP address** (or `localhost`) without a certificate, use `http://`
> instead (e.g. `base_url="http://<host-ip>:8002"`) — `https://<ip>` will fail
> because an IP cannot present a valid certificate.

## Common operations

```python
# Browse organizations and search the catalog
client.list_organizations()
client.search_datasets("storm radar")

# Create a dataset
client.register_dataset(
    name="storm-radar-2025",
    title="Storm radar reflectivity 2025",
    owner_org="atmospheric-research",
    notes="Hourly NEXRAD Level-II composites over CONUS.",
    tags=["radar", "nexrad", "2025"],
)

# Register a URL resource for that dataset
client.register_url(
    resource_name="radar-jan-2025",
    resource_title="Radar reflectivity — January 2025",
    owner_org="atmospheric-research",
    resource_url="https://data.example.org/radar/2025-01.nc",
    file_type="NetCDF",
)

# Register an S3 resource
client.register_s3(
    resource_name="radar-archive-2025",
    resource_title="NEXRAD radar archive, 2025",
    owner_org="atmospheric-research",
    resource_s3="s3://nexrad-archive/2025/",
    notes="Annual archive, partitioned by month.",
)

# Register a Kafka topic
client.register_kafka(
    dataset_name="nexrad-live",
    dataset_title="NEXRAD radar — live stream",
    owner_org="atmospheric-research",
    kafka_topic="nexrad.live",
    kafka_host="kafka.example.org",
    kafka_port=9092,
    dataset_description="Live JSON feed of NEXRAD volume scans.",
)
```

## S3 management from code

```python
# Buckets
client.list_buckets()
client.create_bucket("radar-archive-2025")
client.get_bucket_info("radar-archive-2025")
client.delete_bucket("radar-archive-2025")  # the bucket must be empty

# Objects
client.download_object("radar-archive-2025", "2025-01.nc")
```

The library mirrors the Endpoint's S3 Management UI: uploads, presigned URLs,
metadata reads, and deletes all have method equivalents. Like the UI, they
require the **writer** (or admin) role.

## Typical use cases

- **Bulk import.** Walk a directory tree, create one dataset per top-level
  folder, and register each file inside as a URL or S3 resource.
- **Recurring ingestion.** Run a script on a schedule to register new outputs
  of an instrument or pipeline.
- **CI integration.** Have a CI job publish a versioned dataset after a build.
- **ETL bridges.** Use the catalog as the source of truth for downstream
  processing — read the dataset list from the Endpoint, then process each
  resource.

## Where to find more

- The library on PyPI: <https://pypi.org/project/ndp-ep/>.
- The library source: <https://github.com/sci-ndp/ndp-ep-py>.
- The Endpoint's interactive HTTP API: `<your-endpoint>/ep-api/docs`.
