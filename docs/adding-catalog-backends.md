# Adding New Catalog Backend Implementations

This guide explains how to add support for new catalog backend systems (e.g., Elasticsearch, PostgreSQL, or any other storage system) to the NDP-EP API.

## Table of Contents

1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Step-by-Step Implementation](#step-by-step-implementation)
4. [Example: Adding Elasticsearch Backend](#example-adding-elasticsearch-backend)
5. [Testing Your Implementation](#testing-your-implementation)
6. [Best Practices](#best-practices)

## Overview

The NDP-EP API uses the **Repository Pattern** to abstract catalog operations. This allows you to swap out the underlying storage system (CKAN, MongoDB, etc.) without changing any business logic or API endpoints.

### Current Supported Backends

- **CKAN**: Traditional CKAN catalog system (default)
- **MongoDB**: NoSQL document database

### What You Can Add

Any system that can store and retrieve datasets, resources, and organizations can be implemented as a catalog backend:

- **Elasticsearch**: Full-text search engine
- **PostgreSQL**: Relational database
- **SQLite**: Lightweight file-based database
- **Neo4j**: Graph database
- **Redis**: In-memory data store
- **Custom REST API**: Any external catalog service

## Architecture

```
┌─────────────────────────────────────────┐
│     FastAPI Routes                      │
│     (No changes needed)                 │
└──────────────┬──────────────────────────┘
               │
┌──────────────▼──────────────────────────┐
│     Service Layer                       │
│     (No changes needed)                 │
└──────────────┬──────────────────────────┘
               │
┌──────────────▼──────────────────────────┐
│   CatalogSettings (Factory)             │
│   - Selects repository based on config  │
└──────────────┬──────────────────────────┘
               │
┌──────────────▼──────────────────────────┐
│   DataCatalogRepository Interface       │
│   (Abstract base class)                 │
└──────────────┬──────────────────────────┘
               │
       ┌───────┴────────┬──────────────────┐
       │                │                  │
┌──────▼──────┐  ┌──────▼────────┐  ┌─────▼──────────┐
│  CKAN       │  │  MongoDB      │  │  Your New      │
│  Repository │  │  Repository   │  │  Repository    │
└─────────────┘  └───────────────┘  └────────────────┘
```

## Step-by-Step Implementation

### Step 1: Create Your Repository Class

Create a new file in `api/repositories/` for your backend implementation:

```bash
touch api/repositories/your_backend_repository.py
```

### Step 2: Implement the DataCatalogRepository Interface

Your class must inherit from `DataCatalogRepository` and implement all abstract methods:

```python
# api/repositories/your_backend_repository.py
from typing import Any, Dict, List
from api.repositories.base_repository import DataCatalogRepository

class YourBackendRepository(DataCatalogRepository):
    """
    Your backend implementation of the catalog repository.

    Parameters
    ----------
    connection_params : dict
        Connection parameters specific to your backend
    """

    def __init__(self, connection_params: dict):
        self.client = YourBackendClient(**connection_params)
        # Initialize your connection here

    def package_create(self, **kwargs) -> Dict[str, Any]:
        """Create a package in your backend."""
        # Your implementation here
        # Must return dict with at least {"id": "...", "name": "..."}
        pass

    def package_show(self, id: str) -> Dict[str, Any]:
        """Retrieve a package from your backend."""
        # Your implementation here
        pass

    def package_update(self, **kwargs) -> Dict[str, Any]:
        """Update a package in your backend."""
        # Your implementation here
        pass

    def package_patch(self, **kwargs) -> Dict[str, Any]:
        """Partially update a package in your backend."""
        # Your implementation here
        pass

    def package_delete(self, id: str) -> None:
        """Delete a package from your backend."""
        # Your implementation here
        pass

    def package_search(
        self,
        q: str = "*:*",
        fq: str = "",
        rows: int = 10,
        start: int = 0,
        sort: str = "score desc, metadata_modified desc",
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Search packages in your backend.

        Must return dict with {"count": int, "results": []}
        """
        # Your implementation here
        pass

    def resource_create(self, **kwargs) -> Dict[str, Any]:
        """Create a resource in your backend."""
        # Your implementation here
        pass

    def resource_show(self, id: str) -> Dict[str, Any]:
        """Retrieve a resource from your backend."""
        # Your implementation here
        pass

    def resource_delete(self, id: str) -> None:
        """Delete a resource from your backend."""
        # Your implementation here
        pass

    def organization_create(self, **kwargs) -> Dict[str, Any]:
        """Create an organization in your backend."""
        # Your implementation here
        pass

    def organization_show(self, id: str) -> Dict[str, Any]:
        """Retrieve an organization from your backend."""
        # Your implementation here
        pass

    def organization_list(
        self, all_fields: bool = False, **kwargs
    ) -> List[Dict[str, Any]]:
        """List organizations from your backend."""
        # Your implementation here
        pass

    def organization_delete(self, id: str) -> None:
        """Delete an organization from your backend."""
        # Your implementation here
        pass
```

### Step 3: Register Your Repository in the Module

Update `api/repositories/__init__.py` to export your new repository:

```python
# api/repositories/__init__.py
from api.repositories.base_repository import DataCatalogRepository
from api.repositories.ckan_repository import CKANRepository
from api.repositories.mongodb_repository import MongoDBRepository
from api.repositories.your_backend_repository import YourBackendRepository  # Add this

__all__ = [
    "DataCatalogRepository",
    "CKANRepository",
    "MongoDBRepository",
    "YourBackendRepository",  # Add this
]
```

### Step 4: Add Configuration Settings

Update `api/config/catalog_settings.py` to support your new backend:

```python
# api/config/catalog_settings.py
from api.repositories.your_backend_repository import YourBackendRepository

class CatalogSettings(BaseSettings):
    # Existing settings...
    local_catalog_backend: str = "ckan"

    # Add your backend settings
    your_backend_connection_string: str = "your-default-connection"
    your_backend_param1: str = "default-value"
    your_backend_param2: int = 5432

    @property
    def local_catalog(self) -> DataCatalogRepository:
        backend = self.local_catalog_backend.lower()

        if backend == "your_backend":
            return YourBackendRepository(
                connection_params={
                    "connection_string": self.your_backend_connection_string,
                    "param1": self.your_backend_param1,
                    "param2": self.your_backend_param2,
                }
            )
        elif backend == "mongodb":
            return MongoDBRepository(...)
        elif backend == "ckan":
            return CKANRepository(...)
        else:
            raise ValueError(
                f"Unsupported catalog backend: {backend}. "
                f"Supported backends: 'ckan', 'mongodb', 'your_backend'"
            )
```

### Step 5: Update Environment Configuration

Add your backend configuration to `example.env`:

```bash
# ==============================================
# LOCAL CATALOG CONFIGURATION
# ==============================================

# Backend for local catalog: "ckan", "mongodb", or "your_backend"
LOCAL_CATALOG_BACKEND=ckan

# ... existing CKAN and MongoDB config ...

# ==============================================
# Your Backend Configuration (if LOCAL_CATALOG_BACKEND=your_backend)
# ==============================================

YOUR_BACKEND_CONNECTION_STRING=your-connection-string-here
YOUR_BACKEND_PARAM1=value1
YOUR_BACKEND_PARAM2=5432
```

### Step 6: Add Dependencies

If your backend requires additional Python packages, add them to `requirements.txt`:

```txt
# requirements.txt
...existing packages...
your-backend-client>=1.0.0
```

## Example: Adding Elasticsearch Backend

Here's a complete example of adding Elasticsearch as a catalog backend:

### 1. Create Elasticsearch Repository

```python
# api/repositories/elasticsearch_repository.py
from typing import Any, Dict, List
from datetime import datetime
from elasticsearch import Elasticsearch
from api.repositories.base_repository import DataCatalogRepository

class ElasticsearchRepository(DataCatalogRepository):
    """Elasticsearch implementation of catalog repository."""

    def __init__(self, hosts: List[str], index_prefix: str = "ndp"):
        self.es = Elasticsearch(hosts=hosts)
        self.index_prefix = index_prefix
        self.packages_index = f"{index_prefix}_packages"
        self.resources_index = f"{index_prefix}_resources"
        self.orgs_index = f"{index_prefix}_organizations"

        # Create indices if they don't exist
        self._create_indices()

    def _create_indices(self):
        """Create Elasticsearch indices with mappings."""
        package_mapping = {
            "mappings": {
                "properties": {
                    "id": {"type": "keyword"},
                    "name": {"type": "keyword"},
                    "title": {"type": "text"},
                    "notes": {"type": "text"},
                    "owner_org": {"type": "keyword"},
                    "extras": {"type": "object"},
                    "resources": {"type": "nested"},
                    "metadata_created": {"type": "date"},
                    "metadata_modified": {"type": "date"},
                }
            }
        }

        if not self.es.indices.exists(index=self.packages_index):
            self.es.indices.create(index=self.packages_index, body=package_mapping)

        # Similar for resources and organizations...

    def package_create(self, **kwargs) -> Dict[str, Any]:
        """Create a package in Elasticsearch."""
        import uuid

        package_id = str(uuid.uuid4())
        now = datetime.utcnow().isoformat()

        doc = {
            "id": package_id,
            "name": kwargs.get("name"),
            "title": kwargs.get("title", ""),
            "owner_org": kwargs.get("owner_org"),
            "notes": kwargs.get("notes", ""),
            "extras": kwargs.get("extras", []),
            "resources": [],
            "metadata_created": now,
            "metadata_modified": now,
            "state": "active",
        }

        self.es.index(
            index=self.packages_index,
            id=package_id,
            document=doc,
            refresh=True  # Make immediately searchable
        )

        return doc

    def package_show(self, id: str) -> Dict[str, Any]:
        """Retrieve a package from Elasticsearch."""
        try:
            result = self.es.get(index=self.packages_index, id=id)
            return result["_source"]
        except Exception as e:
            raise Exception(f"Package '{id}' not found: {str(e)}")

    def package_search(
        self,
        q: str = "*:*",
        fq: str = "",
        rows: int = 10,
        start: int = 0,
        sort: str = "score desc, metadata_modified desc",
        **kwargs,
    ) -> Dict[str, Any]:
        """Search packages using Elasticsearch query DSL."""
        query = {
            "query": {
                "query_string": {
                    "query": q if q != "*:*" else "*",
                    "fields": ["title^2", "notes", "name"]
                }
            },
            "from": start,
            "size": rows,
        }

        # Add filters if provided
        if fq:
            # Parse fq and add to query
            pass

        result = self.es.search(index=self.packages_index, body=query)

        return {
            "count": result["hits"]["total"]["value"],
            "results": [hit["_source"] for hit in result["hits"]["hits"]]
        }

    # Implement other methods...
    def package_update(self, **kwargs) -> Dict[str, Any]:
        package_id = kwargs.get("id")
        kwargs["metadata_modified"] = datetime.utcnow().isoformat()

        self.es.update(
            index=self.packages_index,
            id=package_id,
            doc=kwargs,
            refresh=True
        )

        return self.package_show(package_id)

    def package_delete(self, id: str) -> None:
        self.es.delete(index=self.packages_index, id=id, refresh=True)

    # ... implement remaining methods
```

### 2. Register in Catalog Settings

```python
# api/config/catalog_settings.py
from api.repositories.elasticsearch_repository import ElasticsearchRepository

class CatalogSettings(BaseSettings):
    local_catalog_backend: str = "ckan"

    # Elasticsearch settings
    elasticsearch_hosts: List[str] = ["http://localhost:9200"]
    elasticsearch_index_prefix: str = "ndp"

    @property
    def local_catalog(self) -> DataCatalogRepository:
        backend = self.local_catalog_backend.lower()

        if backend == "elasticsearch":
            return ElasticsearchRepository(
                hosts=self.elasticsearch_hosts,
                index_prefix=self.elasticsearch_index_prefix
            )
        # ... other backends
```

### 3. Update Configuration Files

```bash
# example.env
LOCAL_CATALOG_BACKEND=elasticsearch

# ==============================================
# Elasticsearch Configuration
# ==============================================
ELASTICSEARCH_HOSTS=["http://localhost:9200"]
ELASTICSEARCH_INDEX_PREFIX=ndp
```

```txt
# requirements.txt
elasticsearch>=8.0.0
```

## Testing Your Implementation

### 1. Unit Tests

Create unit tests for your repository:

```python
# tests/test_your_backend_repository.py
import pytest
from api.repositories.your_backend_repository import YourBackendRepository

@pytest.fixture
def repository():
    return YourBackendRepository(connection_params={...})

def test_package_create(repository):
    package = repository.package_create(
        name="test-package",
        title="Test Package",
        owner_org="test-org",
        notes="Test description"
    )

    assert "id" in package
    assert package["name"] == "test-package"

def test_package_show(repository):
    # Create a package first
    created = repository.package_create(name="test", title="Test", owner_org="org")

    # Retrieve it
    retrieved = repository.package_show(created["id"])

    assert retrieved["id"] == created["id"]
    assert retrieved["name"] == "test"

# Add more tests...
```

### 2. Integration Tests

Test the full stack with your backend:

```python
# tests/test_integration_your_backend.py
from fastapi.testclient import TestClient
from api.main import app
import os

# Set environment to use your backend
os.environ["LOCAL_CATALOG_BACKEND"] = "your_backend"

client = TestClient(app)

def test_create_s3_resource_with_your_backend():
    response = client.post(
        "/s3",
        json={
            "resource_name": "test-s3",
            "resource_title": "Test S3 Resource",
            "owner_org": "test-org",
            "resource_s3": "s3://bucket/key"
        }
    )

    assert response.status_code == 200
    assert "id" in response.json()
```

## Best Practices

### 1. **Match CKAN's Response Format**

To ensure compatibility, your responses should match CKAN's structure:

```python
# Package response example
{
    "id": "uuid-string",
    "name": "package-name",
    "title": "Package Title",
    "owner_org": "org-id",
    "notes": "Description",
    "extras": [{"key": "k1", "value": "v1"}],
    "resources": [...],
    "metadata_created": "2024-01-01T00:00:00",
    "metadata_modified": "2024-01-01T00:00:00",
    "state": "active"
}
```

### 2. **Handle Errors Gracefully**

Always raise descriptive exceptions:

```python
def package_show(self, id: str) -> Dict[str, Any]:
    try:
        result = self.backend.get(id)
        if not result:
            raise Exception(f"Package '{id}' not found")
        return result
    except ConnectionError as e:
        raise Exception(f"Backend connection error: {str(e)}")
    except Exception as e:
        raise Exception(f"Error retrieving package: {str(e)}")
```

### 3. **Implement Efficient Indexing**

Create indexes for commonly queried fields:

```python
def _create_indexes(self):
    # For MongoDB
    self.packages.create_index("name", unique=True)
    self.packages.create_index("owner_org")
    self.packages.create_index([("title", "text"), ("notes", "text")])
```

### 4. **Support Transactions (if possible)**

For backends that support transactions, use them for multi-step operations:

```python
def package_delete(self, id: str) -> None:
    with self.backend.transaction():
        # Delete resources first
        self.resources.delete_many({"package_id": id})
        # Then delete package
        self.packages.delete_one({"id": id})
```

### 5. **Document Your Implementation**

Add comprehensive docstrings:

```python
class YourBackendRepository(DataCatalogRepository):
    """
    Your Backend implementation of the catalog repository.

    This repository uses YourBackend to store catalog data,
    providing [specific features/advantages].

    Connection Parameters
    ---------------------
    param1 : str
        Description of param1
    param2 : int
        Description of param2

    Examples
    --------
    >>> repo = YourBackendRepository(param1="value", param2=42)
    >>> package = repo.package_create(name="test", title="Test", owner_org="org")

    Notes
    -----
    - [Important note 1]
    - [Important note 2]
    """
```

### 6. **Optimize for Your Backend's Strengths**

Take advantage of your backend's unique features:

- **Elasticsearch**: Use full-text search capabilities
- **PostgreSQL**: Use SQL joins for complex queries
- **Neo4j**: Use graph traversals for relationships
- **Redis**: Use pub/sub for real-time updates

### 7. **Handle Extras/Metadata Properly**

Extras can contain any user-defined metadata:

```python
def package_create(self, **kwargs) -> Dict[str, Any]:
    extras = kwargs.get("extras", [])

    # Convert extras list to dict for easier handling
    extras_dict = {e["key"]: e["value"] for e in extras}

    # Store in your backend's preferred format
    # Convert back to list format when returning
    return {
        "id": package_id,
        "extras": [{"key": k, "value": v} for k, v in extras_dict.items()]
    }
```

## Troubleshooting

### Common Issues

1. **Import Errors**
   - Make sure to add your repository to `__init__.py`
   - Check that all dependencies are in `requirements.txt`

2. **Configuration Not Loading**
   - Verify environment variables are set correctly
   - Check `pydantic_settings` is reading from `.env`

3. **Type Mismatches**
   - Ensure your return types match the interface
   - Use `typing` hints consistently

4. **Tests Failing**
   - Mock external dependencies in unit tests
   - Use test containers for integration tests
   - Clean up test data between tests

## Contributing Your Backend

If you've implemented a backend that others might find useful, consider contributing it to the project:

1. Ensure all tests pass
2. Add comprehensive documentation
3. Update the main README.md
4. Submit a pull request with your implementation

## Resources

- [Repository Pattern Explained](https://martinfowler.com/eaaCatalog/repository.html)
- [CKAN API Documentation](https://docs.ckan.org/en/latest/api/index.html)
- [Python Abstract Base Classes](https://docs.python.org/3/library/abc.html)
- [Pydantic Settings](https://docs.pydantic.dev/latest/concepts/pydantic_settings/)

---

For questions or support, please open an issue on the GitHub repository.
