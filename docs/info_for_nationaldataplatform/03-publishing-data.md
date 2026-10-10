# Publishing data

Publishing on an Endpoint requires the **writer** (or admin) role — see
[Requesting access and the role tiers](02-requesting-access-and-roles.md).

With that role, the navigation bar shows a **`+ New`** menu. It has seven
entries, and each one appears only when the part of the Endpoint it needs is
configured, so the menu never offers something that cannot work:

| Entry | What it is | Shown when the Endpoint has |
|---|---|---|
| **Organization** | A top-level group that owns datasets. | a local catalog |
| **Dataset** | A logical container of related resources, owned by an organization. | a local catalog |
| **Service** | A network-accessible service (REST API, web app, trigger), always under the `services` organization. | a local catalog |
| **Kafka topic** | A streaming data flow registered as a dataset. | Kafka enabled and a local catalog |
| **URL resource** | A link to a file or service (CSV, JSON, NetCDF, stream, …), registered as a dataset. | a local catalog |
| **S3 storage** | The S3 management page: buckets and objects. | S3 enabled |
| **S3 resource** | An object in S3-compatible storage, registered as a dataset. | S3 enabled and a local catalog |

An Endpoint installed with the defaults has no local catalog, S3 or Kafka, so
it shows no `+ New` menu at all. Registering a Kafka topic also writes to the
local catalog, so the Kafka entry needs one too (since 0.34.52; before, it was
shown on an Endpoint with Kafka but no local catalog, where the route it calls,
`POST /kafka`, does not exist).

## A typical publishing flow

1. **Create an Organization** (once per group/lab/project).
2. **Create a Dataset** under that Organization — give it a title, description
   and tags, and optionally resources.
3. **Register URL, S3 or Kafka entries** that point at where the data lives.

You can also register **Services** (an API, a dashboard, a webhook…) — these
appear in the catalog so other users can discover them and call them through
the Endpoint.

## Field cheat-sheet

Required fields in **bold**. Slugs (`name`, `service_name`, `resource_name`,
`dataset_name`) accept lowercase letters, digits, `_` and `-`.

### Organization
**`name`**, **`title`**, `description`.

### Dataset
**`name`**, **`title`**, **`owner_org`**, `notes`, `tags`, `groups`,
`license_id`, `version`, `extras`, `resources`, `private`.

### Service
**`service_name`**, **`service_title`**, **`owner_org`** (must be `services`),
**`service_url`**, `service_type` (the UI offers **API**, **UI** and
**Trigger**, or free text), `notes`, `health_check_url`, `documentation_url`,
`extras` (`requires_auth` set to a true value makes the Endpoint require a
token before forwarding a call to the service).

### URL resource
**`resource_name`**, **`resource_title`**, **`owner_org`**, **`resource_url`**,
`file_type` (one of `stream`, `CSV`, `TXT`, `JSON`, `NetCDF` or custom),
`processing` (type-specific: CSV delimiter and header line, JSON `data_key`,
NetCDF `group`, …), `notes`, `mapping`, `extras`.

### S3 resource
**`resource_name`**, **`resource_title`**, **`owner_org`**, **`resource_s3`**
(`s3://bucket/path` or `http(s)://…`), `notes`, `extras`.

### Kafka topic
**`dataset_name`**, **`dataset_title`**, **`owner_org`**, **`kafka_topic`**,
**`kafka_host`**, **`kafka_port`** (1–65535), `dataset_description`,
`mapping`, `processing`, `extras`.

## Managing what you publish

On the **Search** page, with the **Local** catalog selected, the items you
created yourself carry a **Yours** badge and offer:

- **Delete** — datasets, services, and organizations you own.
- **Publish** — **datasets only**, and only those not yet sent. Publish
  copies the dataset and its resources to the platform's **staging catalog
  (Pre-CKAN)**, marked as submitted for review, and marks the local copy as
  submitted too. It does not publish to the central catalog directly. It
  works only on an Endpoint with the staging catalog configured, which a
  registration with the NDP Federation provides; elsewhere it fails.

## When the data is large

For large object datasets, the writer can use the **S3 storage** page to
create buckets, upload objects (drag-and-drop or file picker), generate
**presigned URLs** for time-limited sharing, view metadata, and delete objects.
It is available only to writers and admins, on an Endpoint with S3 enabled.

## When you have many things to publish

If you have many datasets or files to register, do it from code. The
[`ndp-ep`](https://pypi.org/project/ndp-ep/) Python library performs the
operations on this page from a script — see
[Automating with Python](04-automating-with-python.md).
