# Repository Pattern Architecture

## Overview

The NDP-EP (National Data Platform - Enterprise Platform) implements a **Repository Pattern** for abstracting data catalog backend operations. This architecture enables seamless switching between different catalog implementations (CKAN, MongoDB, or future backends) without changing application code.

## Key Concepts

### What is the Repository Pattern?

The Repository Pattern is a design pattern that abstracts data access logic by creating an intermediary layer between business logic and data sources. Instead of directly accessing databases or external APIs, application code communicates with repositories that provide a consistent interface.

**Benefits:**
- Backend independence: Switch databases/services without code changes
- Testability: Easy to mock repositories for unit tests
- Consistency: Uniform API across different implementations
- Maintainability: Data access logic centralized in one place

---

## Architecture Layers

```
┌─────────────────────────────────┐
│     FastAPI Routes/Endpoints    │  HTTP interface
└────────────┬────────────────────┘
             │
┌────────────▼────────────────────┐
│    Service/Business Logic       │  Domain-specific operations
└────────────┬────────────────────┘
             │
┌────────────▼────────────────────┐
│  Repository Abstraction Layer   │  Uniform interface for data access
└────────────┬────────────────────┘
             │
    ┌────────┴─────────┬──────────┐
    │                  │          │
┌───▼────┐    ┌────────▼──┐  ┌───▼────┐
│ CKAN   │    │ MongoDB    │  │ Future │
│ API    │    │ Database   │  │Backends│
└────────┘    └────────────┘  └────────┘
```

---

## 1. Repository Layer

### Base Repository (`api/repositories/base_repository.py`)

The `DataCatalogRepository` is an abstract base class (ABC) that defines the interface all backends must implement.

**Key Methods:**

#### Package Management
```python
package_create(**kwargs) -> Dict[str, Any]
package_show(id: str) -> Dict[str, Any]
package_update(**kwargs) -> Dict[str, Any]
package_patch(**kwargs) -> Dict[str, Any]
package_delete(id: str) -> None
package_search(q: str, fq: str, rows: int, start: int, sort: str, **kwargs) -> Dict[str, Any]
```

#### Resource Management
```python
resource_create(**kwargs) -> Dict[str, Any]
resource_show(id: str) -> Dict[str, Any]
resource_delete(id: str) -> None
```

#### Organization Management
```python
organization_create(**kwargs) -> Dict[str, Any]
organization_show(id: str) -> Dict[str, Any]
organization_list(all_fields: bool) -> List[Dict[str, Any]]
organization_delete(id: str) -> None
```

#### Health Monitoring
```python
check_health() -> bool
```

### CKAN Repository (`api/repositories/ckan_repository.py`)

Implements the repository interface for **CKAN** (Comprehensive Knowledge Archive Network).

**How it works:**
- Wraps a `ckanapi.RemoteCKAN` client instance
- Delegates all operations to CKAN's action API
- Returns responses in CKAN's standard format

**Example:**
```python
class CKANRepository(DataCatalogRepository):
    def __init__(self, ckan_instance):
        self.ckan = ckan_instance  # RemoteCKAN client
    
    def package_create(self, **kwargs) -> Dict[str, Any]:
        return self.ckan.action.package_create(**kwargs)
    
    def package_search(self, q: str = "*:*", fq: str = "", rows: int = 10, 
                      start: int = 0, sort: str = "score desc, metadata_modified desc",
                      **kwargs) -> Dict[str, Any]:
        return self.ckan.action.package_search(
            q=q, fq=fq, rows=rows, start=start, sort=sort, **kwargs
        )
```

**Characteristics:**
- Direct wrapper around CKAN API
- Minimal transformation needed (CKAN responses already match interface)
- Supports Solr-style full-text search

### MongoDB Repository (`api/repositories/mongodb_repository.py`)

Implements the repository interface for **MongoDB**, allowing it to serve as a drop-in replacement for CKAN.

**Architecture:**
- Collections: `packages`, `resources`, `organizations`
- Each collection has appropriate indexes for performance
- Mimics CKAN's response structure for compatibility

**Key Implementation Details:**

#### Document Structure
```python
# Package document
{
    "id": "uuid",
    "name": "unique_name",
    "title": "Human Title",
    "owner_org": "org_id",
    "notes": "description",
    "resources": [],
    "extras": [{"key": "...", "value": "..."}],
    "metadata_created": "ISO timestamp",
    "metadata_modified": "ISO timestamp",
    "state": "active",
    "type": "dataset"
}

# Resource document
{
    "id": "uuid",
    "package_id": "parent_package_id",
    "name": "resource_name",
    "url": "resource_url",
    "description": "resource_description",
    "format": "CSV|S3|Kafka|...",
    "created": "ISO timestamp",
    "last_modified": "ISO timestamp"
}

# Organization document
{
    "id": "uuid",
    "name": "unique_org_name",
    "title": "Organization Title",
    "description": "org_description",
    "created": "ISO timestamp",
    "state": "active",
    "type": "organization"
}
```

#### Search Implementation
```python
def package_search(self, q: str = "*:*", fq: str = "", fq_list: Optional[List[str]] = None,
                  rows: int = 10, start: int = 0, 
                  sort: str = "score desc, metadata_modified desc",
                  **kwargs) -> Dict[str, Any]:
    # Text search using regex on title, notes, name
    if q and q != "*:*":
        query["$or"] = [
            {"title": {"$regex": re.escape(q), "$options": "i"}},
            {"notes": {"$regex": re.escape(q), "$options": "i"}},
            {"name": {"$regex": re.escape(q), "$options": "i"}},
        ]
    
    # Filter queries (field:value format)
    for filter_item in fq_list:
        field, value = filter_item.split(":", 1)
        query[field] = value.strip('"')
    
    # Execute with pagination and sorting
    return {"count": total_count, "results": results}
```

**Characteristics:**
- Uses MongoDB's native text search capabilities
- Simpler but less feature-rich than Solr
- Supports pagination and filtering
- Perfect for development/testing environments

---

## 2. Configuration & Factory Pattern

### Catalog Settings (`api/config/catalog_settings.py`)

Central configuration module that manages repository instantiation based on environment variables.

```python
class CatalogSettings(BaseSettings):
    # Backend selection for LOCAL catalog only
    local_catalog_backend: str = "ckan"  # "ckan" or "mongodb"
    
    # MongoDB configuration
    mongodb_connection_string: str = "mongodb://localhost:27017"
    mongodb_database: str = "ndp_local_catalog"
    
    @property
    def local_catalog(self) -> DataCatalogRepository:
        """Get repository for local catalog"""
        if self.local_catalog_backend == "mongodb":
            return MongoDBRepository(
                connection_string=self.mongodb_connection_string,
                database_name=self.mongodb_database,
            )
        else:  # "ckan"
            return CKANRepository(ckan_settings.ckan)
    
    @property
    def global_catalog(self) -> DataCatalogRepository:
        """Always returns CKAN for global catalog"""
        return CKANRepository(ckan_settings.ckan_global)
    
    @property
    def pre_catalog(self) -> DataCatalogRepository:
        """Always returns CKAN for PreCKAN staging"""
        return CKANRepository(ckan_settings.pre_ckan)
```

**Key Points:**
- **LOCAL catalog**: Can be CKAN or MongoDB (configurable via `LOCAL_CATALOG_BACKEND`)
- **GLOBAL catalog**: Always CKAN (global NDP instance, read-only)
- **PRE catalog**: Always CKAN (PreCKAN staging environment)
- Factory method pattern enables runtime backend selection

**Environment Variables:**
```bash
LOCAL_CATALOG_BACKEND=mongodb         # "ckan" or "mongodb"
MONGODB_CONNECTION_STRING=mongodb://localhost:27017
MONGODB_DATABASE=ndp_local_catalog
```

---

## 3. Service Layer

Services contain business logic and use repositories for data access. They abstract domain-specific operations.

### Pattern: Service → Repository

**Example: Search Datasource Service**

```python
# api/services/datasource_services/search_datasource.py

async def search_datasource(
    dataset_name: Optional[str] = None,
    dataset_title: Optional[str] = None,
    owner_org: Optional[str] = None,
    resource_format: Optional[str] = None,
    search_term: Optional[str] = None,
    server: Optional[str] = "local",  # "local", "global", or "pre_ckan"
) -> List[DataSourceResponse]:
    """
    Search datasources across different backends.
    """
    
    # Step 1: Get appropriate repository based on server parameter
    if server == "local":
        repository = catalog_settings.local_catalog  # Could be CKAN or MongoDB
    elif server == "global":
        repository = catalog_settings.global_catalog  # Always CKAN
    else:  # "pre_ckan"
        repository = catalog_settings.pre_catalog    # Always CKAN
    
    # Step 2: Build search query
    search_params = []
    if dataset_name:
        search_params.append(f"name:{dataset_name}")
    if dataset_title:
        search_params.append(f"title:{dataset_title}")
    # ... more conditions
    
    query_string = " AND ".join(search_params) if search_params else "*:*"
    
    # Step 3: Execute search (works with any backend)
    results = repository.package_search(
        q=query_string,
        fq_list=fq_list,
        rows=rows,
        start=start,
    )
    
    # Step 4: Transform results to domain model
    processed_results = []
    for dataset in results["results"]:
        # Filter resources based on criteria
        matching_resources = [
            res for res in dataset.get("resources", [])
            if (not resource_format or res.get("format").lower() == resource_format.lower())
        ]
        
        if matching_resources:
            processed_results.append(DataSourceResponse(
                id=dataset["id"],
                name=dataset["name"],
                title=dataset["title"],
                resources=resources_list,
            ))
    
    return processed_results
```

**Key Characteristics:**
- Receives `server` parameter to select catalog
- Uses `catalog_settings` to get appropriate repository
- Doesn't care about backend implementation
- Transforms CKAN/MongoDB response to domain model
- Single code path works for all backends

### Pattern: Organization Management Service

```python
# api/services/organization_services/create_organization.py

def create_organization(
    name: str,
    title: str,
    description: Optional[str] = None,
    server: Literal["local", "pre_ckan"] = "local",
) -> str:
    """Create organization in specified catalog."""
    
    # Get repository based on server
    if server == "pre_ckan":
        repository = catalog_settings.pre_catalog
    else:
        repository = catalog_settings.local_catalog  # CKAN or MongoDB
    
    # Call repository (same code works for both CKAN and MongoDB)
    organization = repository.organization_create(
        name=name,
        title=title,
        description=description
    )
    
    return organization["id"]
```

---

## 4. Routes/Endpoints Layer

Routes receive HTTP requests and delegate to services.

### Pattern: Route → Service → Repository

**Example: Create Dataset Endpoint**

```python
# api/routes/register_routes/post_general_dataset.py

@router.post("/dataset", status_code=status.HTTP_201_CREATED)
async def create_general_dataset_endpoint(
    data: GeneralDatasetRequest,
    server: Literal["local", "pre_ckan"] = Query("local"),
    user_info: Dict[str, Any] = Depends(get_user_for_write_operation),
):
    """
    Create a new general dataset.
    """
    try:
        # Step 1: Determine which repository to use
        if server == "pre_ckan":
            repository = CKANRepository(ckan_settings.pre_ckan)
        else:
            repository = catalog_settings.local_catalog  # Smart selection
        
        # Step 2: Delegate to service
        dataset_id = create_general_dataset(
            name=data.name,
            title=data.title,
            owner_org=data.owner_org,
            notes=data.notes,
            tags=data.tags,
            extras=data.extras,
            resources=resources,
            repository=repository,  # Pass repository to service
            user_info=user_info,
        )
        
        return {"id": dataset_id}
    
    except Exception as exc:
        # Handle errors consistently
        raise HTTPException(status_code=400, detail=str(exc))
```

**Request Flow:**
```
HTTP Request
    ↓
FastAPI Route Handler
    ↓
Get Repository (catalog_settings or explicit)
    ↓
Call Service with Repository
    ↓
Service Uses Repository Methods
    ↓
Repository Executes on CKAN or MongoDB
    ↓
Transform & Return Response
    ↓
HTTP Response
```

---

## 5. How Search Works Across Backends

### Unified Search Interface

Both CKAN and MongoDB implement `package_search()` with the same signature:

```python
def package_search(
    self,
    q: str = "*:*",              # Query string
    fq: str = "",                # Filter query (single string)
    fq_list: Optional[List[str]] = None,  # Filter list
    rows: int = 10,              # Results per page
    start: int = 0,              # Pagination offset
    sort: str = "...",           # Sort specification
    **kwargs
) -> Dict[str, Any]:
    """Returns: {"count": int, "results": [...]}"
```

### CKAN Search
```
Query String: "title:climate AND organization:research"
↓
Solr Full-Text Search Engine
↓
Results sorted by score + metadata_modified
↓
CKAN Response Format
```

### MongoDB Search
```
Query String: "title:climate AND organization:research"
↓
Parse to filters: {"title": "climate", "organization": "research"}
↓
MongoDB find() with regex on text fields
↓
Sort and paginate with MongoDB
↓
Transform to CKAN-compatible format
```

### Service Example: Search with Multiple Backends

```python
async def search_datasource(
    search_term: Optional[str] = None,
    server: Optional[str] = "local",
) -> List[DataSourceResponse]:
    
    # Get appropriate repository
    repository = {
        "local": catalog_settings.local_catalog,      # CKAN or MongoDB
        "global": catalog_settings.global_catalog,    # Always CKAN
        "pre_ckan": catalog_settings.pre_catalog      # Always CKAN
    }[server]
    
    # Same code works whether repository is CKAN or MongoDB
    results = repository.package_search(
        q=search_term,
        rows=1000
    )
    
    # Both backends return data in same format
    # Services don't need to care which backend is used
    for dataset in results["results"]:
        # Process consistently
        ...
```

---

## 6. Backend Comparison

| Feature | CKAN | MongoDB |
|---------|------|---------|
| **Use Case** | Production, complex queries | Development, quick prototyping |
| **Full-Text Search** | Solr-based, advanced | Regex-based, simple |
| **Scalability** | Distributed via Solr | Limited, single instance |
| **Query Language** | Solr syntax | MongoDB filters + regex |
| **Organization Sync** | Real-time | Via application |
| **Performance** | Excellent for complex search | Good for simple queries |
| **Configuration** | Required external Solr | Only MongoDB needed |
| **Best For** | Production deployments | Testing, development, demos |

---

## 7. Adding a New Backend

To add a new catalog backend (e.g., PostgreSQL, Elasticsearch):

### Step 1: Implement the Interface

```python
# api/repositories/custom_repository.py

from api.repositories.base_repository import DataCatalogRepository

class CustomRepository(DataCatalogRepository):
    """Your custom backend implementation."""
    
    def __init__(self, connection_config):
        self.config = connection_config
    
    def package_create(self, **kwargs) -> Dict[str, Any]:
        # Implement using your backend
        pass
    
    def package_search(self, q: str = "*:*", fq: str = "", ...) -> Dict[str, Any]:
        # Implement search in your backend
        # IMPORTANT: Return {"count": int, "results": [...]}
        pass
    
    # ... implement all abstract methods
```

### Step 2: Register in Factory

```python
# api/config/catalog_settings.py

@property
def local_catalog(self) -> DataCatalogRepository:
    backend = self.local_catalog_backend.lower()
    
    if backend == "mongodb":
        return MongoDBRepository(...)
    elif backend == "ckan":
        return CKANRepository(...)
    elif backend == "custom":  # NEW
        return CustomRepository(...)
    else:
        raise ValueError(f"Unsupported backend: {backend}")
```

### Step 3: Update Configuration

```bash
# .env
LOCAL_CATALOG_BACKEND=custom
CUSTOM_CONNECTION_STRING=your_config_here
```

### Step 4: No Service/Route Changes Needed!

All existing services and routes work automatically with the new backend because they use the repository interface.

---

## 8. Key Architectural Decisions

### Why Abstract the Repository?

1. **Flexibility**: Run MongoDB for development, CKAN for production
2. **Testing**: Mock repositories in unit tests without external services
3. **Migration**: Switch backends without code changes
4. **Future-proofing**: Easy to add new backends as requirements evolve

### Why Three Catalogs?

- **Local**: Mutable, organization's own data (CKAN or MongoDB)
- **Global**: Read-only, global NDP catalog (always CKAN)
- **PreCKAN**: Staging environment (always CKAN)

This separation ensures:
- Local catalog can be changed without affecting global
- Users can work in staging before promoting to global
- Different backends can be used for different purposes

### Why MongoDB for Local?

MongoDB is useful when:
- CKAN/Solr infrastructure isn't available
- Fast prototyping is needed
- Full-text search complexity isn't required
- Running in resource-constrained environments

---

## 9. Data Flow Examples

### Example 1: Create Dataset

```
Client: POST /dataset
    ↓
Route: create_general_dataset_endpoint
    ↓ (get repository)
catalog_settings.local_catalog  ← Selects CKAN or MongoDB
    ↓
Service: create_general_dataset
    ↓
Repository: package_create()
    ├─ If CKAN: ckan_instance.action.package_create()
    └─ If MongoDB: insert into packages collection
    ↓
Service: create_resource()
    ↓
Repository: resource_create()
    ├─ If CKAN: ckan_instance.action.resource_create()
    └─ If MongoDB: insert into resources collection
    ↓
Response: {"id": "dataset_uuid"}
```

### Example 2: Search Across Catalogs

```
Client: POST /search with server="local"
    ↓
Route: search_datasource
    ↓ (get repository)
catalog_settings.local_catalog
    ↓
Service: search_datasource
    ├─ Build query: "title:climate"
    ├─ Execute: repository.package_search(q="title:climate")
    │
    ├─ If CKAN backend:
    │  └─ Solr search with full-text scoring
    │
    └─ If MongoDB backend:
       └─ Regex search on title field
    ↓
Transform results to DataSourceResponse
    ↓
Return: List[DataSourceResponse]
```

---

## 10. File Structure Reference

```
api/
├── config/
│   ├── catalog_settings.py      # Repository factory
│   ├── ckan_settings.py         # CKAN configuration
│   └── ...
├── repositories/
│   ├── base_repository.py       # Abstract interface
│   ├── ckan_repository.py       # CKAN implementation
│   ├── mongodb_repository.py    # MongoDB implementation
│   └── __init__.py
├── services/
│   ├── datasource_services/
│   │   ├── search_datasource.py        # Uses repository
│   │   └── add_datasource.py           # Uses repository
│   ├── organization_services/
│   │   ├── create_organization.py      # Uses repository
│   │   ├── list_organization.py        # Uses repository
│   │   └── ...
│   ├── dataset_services/
│   │   ├── general_dataset.py          # Uses repository
│   │   └── ...
│   └── ...
└── routes/
    ├── register_routes/
    │   ├── post_general_dataset.py     # Gets repository, calls service
    │   ├── post_organization.py
    │   └── ...
    ├── search_routes/
    │   ├── post_search_datasource_route.py  # Gets repository, calls service
    │   └── ...
    ├── delete_routes/
    │   └── delete_dataset.py
    └── ...
```

---

## Summary

The **Repository Pattern** in NDP-EP provides:

1. **Abstraction**: Services and routes don't know about backend implementation
2. **Flexibility**: Switch between CKAN and MongoDB with a single environment variable
3. **Consistency**: All backends conform to the same interface
4. **Testability**: Easy to mock repositories in tests
5. **Extensibility**: Adding new backends requires only implementing the interface

The architecture enables:
- **Local catalog** to use CKAN (production) or MongoDB (development)
- **Global catalog** to always use CKAN (global NDP instance)
- **Services** to work transparently across any backend
- **Routes** to route requests without caring about implementation details

This design has proven essential for the project's flexibility and ease of deployment in different environments.
