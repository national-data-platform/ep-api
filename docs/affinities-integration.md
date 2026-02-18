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

### Service Registration

When you register a service via `POST /services`:

1. The service is created in the local catalog
2. NDP-EP registers the service in Affinities (`POST /services/`)
3. A relationship is created between the service and this endpoint (`POST /service-endpoints/`)

## Error Handling

The Affinities integration is **non-blocking**:

- If Affinities is unreachable or returns an error, the main operation (dataset/service creation) still succeeds
- Errors are logged as warnings but do not affect the API response
- This ensures that Affinities availability does not impact NDP-EP functionality

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

1. Check that `AFFINITIES_ENABLED=True`
2. Verify `AFFINITIES_URL` is correct and accessible
3. Confirm `AFFINITIES_EP_UUID` is a valid UUID from Affinities
4. Check the NDP-EP logs for warning messages

### Testing the Connection

You can verify the Affinities API is accessible:

```bash
curl -X GET "https://your-affinities-api/endpoints/"
```

This should return a list of registered endpoints.
