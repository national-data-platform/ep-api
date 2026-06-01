# Publishing data

Publishing on an Endpoint requires the **writer** (or admin) role — see
[Requesting access and the role tiers](02-requesting-access-and-roles.md).

Once you have a role, the navigation bar shows a **`+ New`** menu. The menu
groups every creation flow the Endpoint offers — six in total, split into
**catalog containers** and **data resources**.

## At a glance

| Kind | What it is |
|---|---|
| **Organization** | A top-level group that owns datasets and services. |
| **Dataset** | A logical container of related resources, owned by an organization. |
| **Service** | A network-accessible service (REST API, web app, etc.) owned by an organization. |
| **URL resource** | A link to a file or service (CSV, JSON, NetCDF, stream, …). |
| **S3 resource** | An object in S3-compatible storage. |
| **Kafka topic** | A streaming data flow registered as a system dataset. |

Catalog containers (Organization, Dataset, Service) are the things users
**search and browse**. Data resources (URL, S3, Kafka) live **inside a dataset**
and point at the actual data.

## A typical publishing flow

1. **Create an Organization** (once per group/lab/project).
2. **Create a Dataset** under that Organization — give it a title, description
   and tags.
3. **Add one or more resources** to the dataset: a URL to a file, an object in
   S3, or a Kafka topic — whichever describes where the data lives.

You can also register **Services** (an API, a dashboard, a webhook…) under the
special `services` organization — these appear in the catalog so other users
can discover and call them.

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
**`service_url`**, `service_type` (one of **API**, **UI**, **Trigger** or
free-text), `notes`, `health_check_url`, `documentation_url`, `extras`.

### URL resource
**`resource_name`**, **`resource_title`**, **`owner_org`**, **`resource_url`**,
`file_type` (one of `stream`, `CSV`, `TXT`, `JSON`, `NetCDF` or custom),
`processing` (type-specific: CSV delimiter and header line, JSON `data_key`,
NetCDF `group`, …), `notes`, `mapping`, `extras`.

### S3 resource
**`resource_name`**, **`resource_title`**, **`owner_org`**, **`resource_s3`**
(`s3://bucket/path` or `http(s)://…`), **`notes`** (may be empty), `extras`.

### Kafka topic
**`dataset_name`**, **`dataset_title`**, **`owner_org`**, **`kafka_topic`**,
**`kafka_host`**, **`kafka_port`** (1–65535), **`dataset_description`**,
`mapping`, `processing`, `extras`.

## Managing what you publish

On the **Search** page, your own items expose **Publish** and **Delete**
actions. Use them to push a dataset upstream (when the Endpoint is connected
to a staging Pre-CKAN or to the federation) or to retire it.

## When the data is large

For large object datasets, the writer can also use the **S3 Management** tool
to create buckets, upload objects (drag-and-drop or file picker), generate
**presigned URLs** for time-limited sharing, view metadata, and delete objects.
S3 Management is restricted to writers and admins.

## When you have many things to publish

If you have many datasets or files to register, do it from code. The
[`ndp-ep`](https://pypi.org/project/ndp-ep/) Python library performs every
operation in this page from a script — see
[Automating with Python](04-automating-with-python.md).
