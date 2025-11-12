# Repository Pattern - Quick Reference Guide

## TL;DR - Key Points

1. **Abstract Interface** (`base_repository.py`): Defines what all backends must implement
2. **Two Implementations**: CKAN wrapper, MongoDB native implementation
3. **Factory Pattern** (`catalog_settings.py`): Creates the right repository based on config
4. **Single Code Path**: Services and routes work with any backend
5. **Three Catalogs**: Local (configurable), Global (always CKAN), PreCKAN (always CKAN)

---

## File Quick Map

```
api/repositories/
├── base_repository.py          ← Abstract interface (DataCatalogRepository)
├── ckan_repository.py          ← CKAN implementation
├── mongodb_repository.py       ← MongoDB implementation
└── __init__.py                 ← Exports all implementations

api/config/
└── catalog_settings.py         ← Factory (creates repositories)

api/services/
├── datasource_services/        ← Uses catalog_settings.local_catalog
├── organization_services/      ← Uses catalog_settings.local_catalog
└── dataset_services/           ← Uses provided repository

api/routes/
├── register_routes/
├── search_routes/
└── delete_routes/
```

---

## How to Use Repositories

### In a Service Function

```python
from api.config.catalog_settings import catalog_settings

def create_dataset(name, title, owner_org):
    # Get repository (CKAN or MongoDB, depending on config)
    repository = catalog_settings.local_catalog
    
    # Call repository method - works with any backend
    dataset = repository.package_create(
        name=name,
        title=title,
        owner_org=owner_org
    )
    
    return dataset["id"]
```

### Supporting Multiple Servers

```python
def search_datasets(query, server="local"):
    # Get appropriate repository
    if server == "global":
        repo = catalog_settings.global_catalog
    elif server == "pre_ckan":
        repo = catalog_settings.pre_catalog
    else:  # "local"
        repo = catalog_settings.local_catalog
    
    # Same code works for all
    return repo.package_search(q=query, rows=100)
```

### In a Route Handler

```python
from fastapi import APIRouter, Query
from api.config import catalog_settings, ckan_settings
from api.repositories import CKANRepository

@router.post("/dataset")
def create_dataset_endpoint(data, server: str = Query("local")):
    if server == "pre_ckan":
        repository = CKANRepository(ckan_settings.pre_ckan)
    else:
        repository = catalog_settings.local_catalog
    
    # Pass to service or use directly
    return create_dataset(
        name=data.name,
        title=data.title,
        owner_org=data.owner_org,
        repository=repository
    )
```

---

## Core Methods Reference

### Package (Dataset) Methods

```python
# Create
package = repo.package_create(
    name="my_dataset",
    title="My Dataset",
    owner_org="organization_id",
    notes="Description",
    extras=[{"key": "custom_field", "value": "value"}]
)
# Returns: {"id": "uuid", "name": "my_dataset", ...}

# Retrieve
package = repo.package_show(id="uuid_or_name")
# Returns: {"id": "uuid", ...}

# Update (full)
package = repo.package_update(
    id="uuid",
    title="New Title",
    notes="New Description"
)
# Returns: updated package dict

# Update (partial)
package = repo.package_patch(
    id="uuid",
    title="Only Update Title"
)
# Returns: updated package dict

# Delete
repo.package_delete(id="uuid")

# Search
results = repo.package_search(
    q="search term",           # Text query
    fq_list=["org:my_org"],    # Filters
    rows=50,                   # Page size
    start=0,                   # Offset
    sort="metadata_modified desc"
)
# Returns: {"count": 100, "results": [...]}
```

### Resource Methods

```python
# Create
resource = repo.resource_create(
    package_id="dataset_uuid",
    name="Resource Name",
    url="http://example.com/data.csv",
    format="CSV",
    description="Resource Description"
)
# Returns: {"id": "uuid", ...}

# Retrieve
resource = repo.resource_show(id="uuid")
# Returns: {"id": "uuid", ...}

# Delete
repo.resource_delete(id="uuid")
```

### Organization Methods

```python
# Create
org = repo.organization_create(
    name="my_org",
    title="My Organization",
    description="Org Description"
)
# Returns: {"id": "uuid", "name": "my_org", ...}

# Retrieve
org = repo.organization_show(id="uuid_or_name")
# Returns: {"id": "uuid", ...}

# List
orgs = repo.organization_list(all_fields=True)
# Returns: [{"id": "uuid", "name": "org1"}, ...]

# Delete
repo.organization_delete(id="uuid")
```

### Health Check

```python
is_healthy = repo.check_health()
# Returns: True or False
```

---

## Configuration

### Environment Variables

```bash
# Backend selection for LOCAL catalog
LOCAL_CATALOG_BACKEND=mongodb  # or "ckan"

# MongoDB configuration (if LOCAL_CATALOG_BACKEND=mongodb)
MONGODB_CONNECTION_STRING=mongodb://localhost:27017
MONGODB_DATABASE=ndp_local_catalog

# CKAN configuration (for all catalogs)
CKAN_SITE_URL=http://localhost:5000
CKAN_API_TOKEN=your_api_token
CKAN_GLOBAL_URL=http://global-ckan.example.com
CKAN_GLOBAL_API_TOKEN=token
PRE_CKAN_URL=http://pre-ckan.example.com
PRE_CKAN_API_TOKEN=token
```

### In Code

```python
from api.config.catalog_settings import catalog_settings

# Access repositories
local_repo = catalog_settings.local_catalog    # CKAN or MongoDB
global_repo = catalog_settings.global_catalog  # Always CKAN
pre_repo = catalog_settings.pre_catalog        # Always CKAN

# Get by name
repo = catalog_settings.get_repository_by_name("local")
```

---

## Common Patterns

### Pattern 1: Simple CRUD on Local Catalog

```python
def manage_dataset(dataset_id, title):
    repo = catalog_settings.local_catalog
    
    # Show
    dataset = repo.package_show(id=dataset_id)
    print(f"Current title: {dataset['title']}")
    
    # Update
    updated = repo.package_update(id=dataset_id, title=title)
    return updated["id"]
```

### Pattern 2: Search with Filters

```python
def search_org_datasets(org_name, format="csv"):
    repo = catalog_settings.local_catalog
    
    results = repo.package_search(
        q="*:*",  # All packages
        fq_list=[
            f"owner_org:{org_name}",
            f"resource_format:{format}"
        ],
        rows=100
    )
    
    return results["results"]
```

### Pattern 3: Create Dataset with Resources

```python
def create_full_dataset(dataset_data, resources_data):
    repo = catalog_settings.local_catalog
    
    # Create package
    package = repo.package_create(**dataset_data)
    package_id = package["id"]
    
    # Create resources
    for resource in resources_data:
        repo.resource_create(
            package_id=package_id,
            **resource
        )
    
    return package_id
```

### Pattern 4: Multi-Server Comparison

```python
def compare_datasets(query):
    results = {}
    
    for server_name in ["local", "global"]:
        repo = catalog_settings.get_repository_by_name(server_name)
        results[server_name] = repo.package_search(q=query, rows=10)
    
    return results
```

---

## Testing with Mock Repositories

```python
from unittest.mock import Mock
from api.repositories import DataCatalogRepository

# Create mock repository
mock_repo = Mock(spec=DataCatalogRepository)
mock_repo.package_search.return_value = {
    "count": 1,
    "results": [{"id": "test_id", "name": "test"}]
}

# Use in test
def test_search(mock_repo):
    results = search_datasets(query="test", repo=mock_repo)
    assert len(results["results"]) == 1
    mock_repo.package_search.assert_called_once()
```

---

## CKAN vs MongoDB Quick Comparison

| Feature | CKAN | MongoDB |
|---------|------|---------|
| **Search** | Solr full-text (fast) | Regex on fields (simple) |
| **Setup** | Requires Solr, PostgreSQL | Single DB connection |
| **For** | Production | Development/Testing |
| **Complex Queries** | Yes | Limited |
| **Scaling** | Yes (via Solr) | Limited |

---

## Troubleshooting

### "Organization does not exist" Error

**Cause**: Creating dataset with invalid `owner_org`

**Solution**: 
```python
# Ensure organization exists first
repo = catalog_settings.local_catalog
orgs = repo.organization_list()
assert "my_org" in orgs

# Then create dataset
repo.package_create(owner_org="my_org", ...)
```

### "Package with name X already exists"

**Cause**: Duplicate package name (names must be unique)

**Solution**:
```python
# Use UUID or timestamp in name
import uuid
package_name = f"dataset_{uuid.uuid4().hex[:8]}"
```

### Search returns no results with MongoDB

**Cause**: MongoDB regex search is simpler than Solr

**Solution**:
- Keep search terms simple
- Check exact field names
- Use `fq_list` for precise filtering

### "No scheme supplied" error

**Cause**: CKAN server not configured or unreachable

**Solution**:
```bash
# Check configuration
echo $CKAN_SITE_URL
# Should be http://... or https://...

# Check server is running
curl http://localhost:5000/api/3/action/status_show
```

---

## Adding a New Backend

1. **Create implementation**:
```python
# api/repositories/custom_repository.py
from api.repositories.base_repository import DataCatalogRepository

class CustomRepository(DataCatalogRepository):
    def package_create(self, **kwargs): ...
    def package_search(self, q, fq, ...): ...
    # ... all other methods
```

2. **Register in factory**:
```python
# api/config/catalog_settings.py
@property
def local_catalog(self) -> DataCatalogRepository:
    if self.local_catalog_backend == "custom":
        return CustomRepository(...)
    # ...
```

3. **Update .env**:
```bash
LOCAL_CATALOG_BACKEND=custom
```

4. **No other changes needed!** Services and routes work automatically.

---

## Key Takeaways

1. **Always get repository from `catalog_settings`** (except pre_ckan in routes)
2. **Same interface for all backends** - code is backend-agnostic
3. **Three catalogs serve different purposes** - don't mix them up
4. **Services should accept optional repository parameter** - enables testing
5. **Routes determine backend** - services use what they're given

---

For detailed information, see:
- `repository-pattern-architecture.md` - Full documentation
- `architecture-diagrams.md` - Visual references
- `adding-catalog-backends.md` - Extending with new backends
