# Affinities Integration

This document describes how to configure and use the NDP Affinities integration in NDP-EP.

## Overview

NDP Affinities is a service that tracks relationships between datasets, services, and endpoints across the NDP ecosystem. When enabled, NDP-EP automatically registers datasets and services in Affinities, creating a federated view of all data assets.

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `AFFINITIES_ENABLED` | `False` | Enable/disable Affinities integration |
| `AFFINITIES_URL` | - | Base URL of the Affinities API |
| `AFFINITIES_EP_UUID` | - | UUID of this endpoint in Affinities |
| `AFFINITIES_TIMEOUT` | `30` | Request timeout in seconds |

### Setup Steps

1. **Register your endpoint in Affinities**

   First, manually register your NDP-EP instance in the Affinities system:

   ```bash
   curl -X POST "https://your-affinities-api/endpoints/" \
     -H "Content-Type: application/json" \
     -d '{
       "kind": "ndp-ep",
       "url": "https://your-ndp-ep-url",
       "metadata": {
         "name": "My NDP Endpoint",
         "organization": "My Organization"
       }
     }'
   ```

   This returns a response with a `uid` field - save this UUID.

2. **Configure NDP-EP**

   Add the following to your `.env` file:

   ```env
   AFFINITIES_ENABLED=True
   AFFINITIES_URL=https://your-affinities-api
   AFFINITIES_EP_UUID=550e8400-e29b-41d4-a716-446655440000
   ```

3. **Restart NDP-EP**

   After updating the configuration, restart your NDP-EP instance.

## How It Works

When Affinities integration is enabled:

### Dataset Registration

When you create a dataset via `POST /dataset`:

1. The dataset is created in the local catalog (CKAN or MongoDB)
2. NDP-EP registers the dataset in Affinities (`POST /datasets/`)
3. A relationship is created between the dataset and this endpoint (`POST /dataset-endpoints/`)
4. An affinity triple is created for the pair (`POST /affinities/`), **only if
   step 3 succeeded** — a triple built on a relationship that does not exist
   names an endpoint Affinities cannot resolve
5. The UUID Affinities assigned is stored on the dataset as the
   `ndp_affinity_uuid` extra, whether or not step 3 succeeded, since it is the
   only reference back to the record that was created

### Service Registration

When you register a service via `POST /services`:

1. The service is created in the local catalog
2. NDP-EP registers the service in Affinities (`POST /services/`)
3. A relationship is created between the service and this endpoint (`POST /service-endpoints/`)
4. An affinity triple is created, under the same condition as for datasets
5. The assigned UUID is stored on the service as `ndp_affinity_uuid`

## Error Handling

The Affinities integration is **non-blocking**:

- If Affinities is unreachable or returns an error, the main operation (dataset/service creation) still succeeds
- This ensures that Affinities availability does not impact NDP-EP functionality

Non-blocking is not silent. A record that Affinities accepted but refused to
link to this endpoint is logged at **error** level, naming the record, the
endpoint UUID it was refused for and the setting to look at, and no affinity
triple is created for it. The registration still reports success to the
caller, because the dataset or service itself was created; what failed is its
attribution, and that belongs in the logs and in `GET /ready`, not in a failed
write.

## Metadata Stored in Affinities

### For Datasets

```json
{
  "title": "Dataset title",
  "source_ep": "your-ep-uuid",
  "metadata": {
    "name": "dataset_name",
    "owner_org": "organization",
    "local_id": "local-catalog-id",
    "notes": "Description",
    "tags": ["tag1", "tag2"]
  }
}
```

### For Services

```json
{
  "type": "service_type",
  "openapi_url": "documentation_url",
  "source_ep": "your-ep-uuid",
  "metadata": {
    "service_name": "my_service",
    "service_title": "My Service",
    "service_url": "https://service-url",
    "local_id": "local-catalog-id",
    "notes": "Description"
  }
}
```

## Troubleshooting

### Integration Not Working

Start with `GET /ready`, which reports the integration under `affinities`:

```json
{
  "checks": {
    "affinities": {
      "status": "up",
      "latency_ms": 12.4,
      "endpoint_registered": false,
      "detail": "Affinities does not know endpoint 550e8400-..."
    }
  }
}
```

- `status` is `disabled` when the integration is off or incompletely
  configured, `down` when Affinities did not answer, `up` otherwise
- `endpoint_registered` is `true` when Affinities knows your
  `AFFINITIES_EP_UUID`, `false` when it does not, and `null` when the question
  could not be answered
- `endpoint_registered: false` is the failure to look for first: everything
  this Endpoint registers is accepted and then attributed to nobody

Affinities is reported but deliberately does not affect the readiness verdict,
so `/ready` stays `healthy` with the integration broken or down. No request
reads from Affinities, and taking the Endpoint out of rotation over it would
stop the catalog for a system that serves no traffic. The result is cached for
30 seconds, so a fresh probe can lag a configuration change by that much.

If that entry looks correct and registration still is not working:

1. Check that `AFFINITIES_ENABLED=True`
2. Verify `AFFINITIES_URL` is correct and accessible
3. Check the NDP-EP logs for errors naming the endpoint UUID

### Testing the Connection

You can verify the Affinities API is accessible:

```bash
curl -X GET "https://your-affinities-api/ep"
```

This should return a list of registered endpoints. To check one directly,
which is what `GET /ready` does:

```bash
curl -X GET "https://your-affinities-api/ep/$AFFINITIES_EP_UUID"
```

A `404` here means Affinities does not have that endpoint, and no dataset or
service registered from this Endpoint can be linked to it.
