# Architecture Diagrams and Visual References

This document provides visual diagrams to complement the Repository Pattern Architecture documentation.

## 1. Overall System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Client Applications                       │
│              (Web UI, Mobile Apps, Scripts)                 │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       │ HTTP/REST API
                       │
┌──────────────────────▼──────────────────────────────────────┐
│                   FastAPI Application                        │
│  ┌─────────────────────────────────────────────────────┐   │
│  │              Authentication & Authorization          │   │
│  └─────────────────────────────────────────────────────┘   │
└──────────────────────┬──────────────────────────────────────┘
                       │
        ┌──────────────┼──────────────┐
        │              │              │
┌───────▼────┐  ┌─────▼──────┐  ┌───▼────────┐
│  Register  │  │   Search   │  │   Update   │
│   Routes   │  │   Routes   │  │   Routes   │
└───────┬────┘  └─────┬──────┘  └───┬────────┘
        │             │             │
        └─────────────┼─────────────┘
                      │
                      │ Delegate to Services
                      │
┌─────────────────────▼──────────────────────────────────────┐
│                    Service Layer                            │
│  ┌──────────────────┐  ┌──────────────────────────┐        │
│  │ Organization     │  │ Datasource/Search        │        │
│  │ Services         │  │ Services                 │        │
│  └────────┬─────────┘  └──────────┬───────────────┘        │
│           │                       │                         │
│  ┌────────▼──────────────────────▼──────────┐             │
│  │      Dataset Services                    │             │
│  └────────┬──────────────────────────────────┘             │
│           │                                                 │
└───────────┼─────────────────────────────────────────────────┘
            │
            │ Use Repository Interface
            │
┌───────────▼──────────────────────────────────────────────────┐
│           Repository Abstraction Layer                        │
│  ┌──────────────────────────────────────────────────────┐   │
│  │       DataCatalogRepository (Abstract)               │   │
│  │  - package_*() methods                              │   │
│  │  - resource_*() methods                             │   │
│  │  - organization_*() methods                         │   │
│  │  - check_health()                                   │   │
│  └──────────────────────────────────────────────────────┘   │
└───┬──────────────────┬──────────────────┬──────────────────┘
    │                  │                  │
┌───▼────────┐  ┌──────▼──────┐  ┌──────▼──────┐
│    CKAN    │  │   MongoDB   │  │  Future     │
│ Repository │  │ Repository  │  │ Repository  │
└───┬────────┘  └──────┬──────┘  └──────┬──────┘
    │                  │                │
┌───▼────────┐  ┌──────▼──────┐  ┌──────▼──────┐
│  CKAN API  │  │  MongoDB    │  │  Custom     │
│   Client   │  │  Connection │  │  Backend    │
└─────────────  └─────────────┘  └─────────────┘
```

## 2. Request Flow: Create Dataset

```
┌─────────────────────────────────────────────────────────────┐
│  POST /dataset                                              │
│  Body: {name, title, owner_org, resources, extras}         │
└──────────────────┬──────────────────────────────────────────┘
                   │
       ┌───────────▼──────────────┐
       │  Authentication Check    │
       │  Authorization Check     │
       └───────────┬──────────────┘
                   │
       ┌───────────▼────────────────────────┐
       │  post_general_dataset_endpoint()   │
       │  - Extract server parameter        │
       │  - Get repository from settings    │
       └───────────┬────────────────────────┘
                   │
       ┌───────────▼──────────────────────┐
       │ catalog_settings factory         │
       │ (Choose backend)                  │
       └───────┬───────────────────────────┘
               │
       ┌───────┴──────────┐
       │                  │
   ┌───▼───┐          ┌───▼────┐
   │CKAN?  │          │MongoDB?│
   └───┬───┘          └───┬────┘
       │                  │
   ┌───▼───────┐      ┌───▼──────────┐
   │CKANRepos- │      │MongoDBRepos- │
   │itory     │      │itory         │
   └───┬───────┘      └───┬──────────┘
       │                  │
       └─────────┬────────┘
                 │
       ┌─────────▼──────────────────┐
       │ create_general_dataset()   │
       │ (Service layer)             │
       │ - Validate input            │
       │ - Inject NDP metadata      │
       │ - Call repository methods   │
       └─────────┬──────────────────┘
                 │
       ┌─────────▼──────────────────────┐
       │ repository.package_create()     │
       │ Create package/dataset          │
       └─────────┬──────────────────────┘
                 │
       ┌─────────▼──────────────────────┐
       │ repository.resource_create()    │
       │ Create resource for each item   │
       └─────────┬──────────────────────┘
                 │
       ┌─────────▼──────────────────┐
       │ Response: {id: dataset_id} │
       └─────────────────────────────┘
```

## 3. Request Flow: Search Datasources

```
┌────────────────────────────────────────────────────┐
│  POST /search                                      │
│  Body: {search_term, dataset_name, server: local} │
└─────────────┬────────────────────────────────────┘
              │
   ┌──────────▼────────────────┐
   │  search_datasource()      │
   │  (Route)                   │
   └──────────┬─────────────────┘
              │
   ┌──────────▼──────────────────────┐
   │ catalog_settings factory        │
   │ (Get repository by server)      │
   │ server="local" →                │
   │ local_catalog property          │
   └──────────┬──────────────────────┘
              │
        ┌─────┴──────────┐
        │                │
    ┌───▼────┐       ┌───▼─────┐
    │ CKAN   │       │ MongoDB  │
    │enabled?│       │enabled?  │
    └───┬────┘       └───┬──────┘
        │                │
   ┌────▼────┐      ┌────▼────────┐
   │CKANRepo │      │MongoDBRepo  │
   └────┬────┘      └────┬────────┘
        │                │
        └────┬───────────┘
             │
   ┌─────────▼────────────────────────────┐
   │ datasource_services.search_datasource│
   │ (Service layer)                       │
   │ - Build query string                 │
   │ - Apply filters                      │
   │ - Call repository.package_search()   │
   └─────────┬────────────────────────────┘
             │
   ┌─────────▼──────────────────┐
   │ repository.package_search()│
   │                            │
   │ If CKAN:                   │
   │  - Solr query              │
   │  - Full-text search        │
   │                            │
   │ If MongoDB:                │
   │  - Regex search            │
   │  - Filter queries          │
   └─────────┬──────────────────┘
             │
   ┌─────────▼────────────────────┐
   │ Transform results            │
   │ (DataSourceResponse model)   │
   └─────────┬────────────────────┘
             │
   ┌─────────▼────────────────────┐
   │ Return: List[DataSourceResp] │
   └────────────────────────────┘
```

## 4. Repository Pattern: Backend Switching

```
                   Service Layer
                        │
                        │ repository.package_search(q="climate")
                        │
                ┌───────▼──────────┐
                │ Repository       │
                │ Interface        │
                └───────┬──────────┘
                        │
           ┌────────────┼────────────┐
           │            │            │
      ┌────▼─────┐  ┌───▼────┐  ┌──▼────────┐
      │ CKAN     │  │MongoDB │  │ Future    │
      │Repo      │  │Repo    │  │ Repo      │
      └────┬─────┘  └───┬────┘  └──┬────────┘
           │            │         │
      ┌────▼─────┐  ┌───▼────┐  ┌──▼────────┐
      │ CKAN API │  │MongoDB │  │ Custom    │
      │ (Solr)   │  │Driver  │  │ Backend   │
      └──────────┘  └────────┘  └───────────┘

Same Service Code → Different Backends
Different Implementations → Same Response Format
```

## 5. Data Model: Package Structure

```
Package (Dataset)
├── id (UUID)
├── name (unique)
├── title
├── owner_org (organization ID)
├── notes (description)
├── state ("active")
├── type ("dataset")
├── metadata_created (ISO timestamp)
├── metadata_modified (ISO timestamp)
│
├── resources (array)
│  └── Resource
│     ├── id (UUID)
│     ├── package_id (parent package)
│     ├── name
│     ├── url
│     ├── description
│     ├── format (CSV, S3, Kafka, URL, etc.)
│     ├── created (ISO timestamp)
│     └── last_modified (ISO timestamp)
│
├── extras (array)
│  └── Extra
│     ├── key (field name)
│     └── value (field value)
│
├── tags (array)
│  └── Tag
│     ├── id (UUID)
│     ├── name
│     └── vocabulary_id
│
└── organization (nested object)
   ├── id
   ├── name
   └── title
```

## 6. Three-Catalog Architecture

```
┌──────────────────────────────────────────────────────────┐
│                    NDP-EP Application                     │
└──────────────────────────────────────────────────────────┘
                        │
    ┌───────────────────┼───────────────────┐
    │                   │                   │
    
┌───▼──────────┐  ┌─────▼──────┐  ┌────────▼───┐
│   LOCAL      │  │   GLOBAL   │  │  PRE-CKAN  │
│  CATALOG     │  │  CATALOG   │  │  CATALOG   │
├──────────────┤  ├────────────┤  ├────────────┤
│              │  │            │  │            │
│ Mutable      │  │ Read-only  │  │ Staging    │
│ Configurable│  │ Reference  │  │ Testing    │
│ Backend:    │  │            │  │            │
│             │  │ Always CKAN│  │ Always CKAN│
│ CKAN        │  │            │  │            │
│  or         │  │ Global NDP │  │ Pre-release│
│ MongoDB     │  │ Data Hub   │  │ Environment│
│             │  │            │  │            │
└────┬────────┘  └──────┬─────┘  └────┬───────┘
     │                  │             │
     │                  │             │
├─────────────┐  ┌──────────────┐  ┌──────────┐
│ Organization│  │  Read-only   │  │ Promote  │
│'s data      │  │  references  │  │ datasets │
│             │  │  for global  │  │ to global│
│ Write:      │  │  integration │  │ from pre │
│ Datasets    │  │              │  │          │
│ Resources   │  │ Use for:     │  │ Validate │
│ Orgs        │  │ - Integration│  │ before   │
│             │  │ - Metrics    │  │ going    │
│ Read:       │  │ - Analytics  │  │ global   │
│ View own    │  │              │  │          │
│ data        │  │ Do NOT write │  │ Do NOT   │
│             │  │              │  │ write    │
└─────────────┘  └──────────────┘  └──────────┘
```

## 7. Configuration & Factory Pattern

```
┌─────────────────────────────────┐
│  Environment Variables           │
│  .env file                       │
├─────────────────────────────────┤
│                                 │
│ LOCAL_CATALOG_BACKEND=mongodb   │
│ MONGODB_CONNECTION_STRING=...   │
│ MONGODB_DATABASE=ndp_local      │
│                                 │
│ (+ CKAN configs for all)        │
│                                 │
└────────────┬────────────────────┘
             │
     ┌───────▼────────────┐
     │ CatalogSettings    │
     │ (Configuration     │
     │  class)            │
     └───────┬────────────┘
             │
     ┌───────┴─────────────────┐
     │                         │
 ┌───▼────┐  ┌────────────┐  ┌─▼────────┐
 │ local  │  │  global    │  │   pre    │
 │_cat    │  │_cat        │  │_cat      │
 │alog()  │  │alog()      │  │alog()    │
 └───┬────┘  └──────┬─────┘  └─┬────────┘
     │              │         │
 ┌───▼────┐     ┌───▼──┐  ┌──▼──────┐
 │Factory │     │CKAN  │  │ CKAN    │
 │Selection   │ │Repo  │  │ Repo    │
 │Based on │  │      │  │         │
 │CONFIG  │  │      │  │         │
 └────────┘  └──────┘  └─────────┘
     │
  ┌──┴──────────────────┐
  │                     │
┌─▼───────────┐  ┌──────▼────┐
│ CKAN Repo   │  │MongoDB Repo│
│ (if CKAN)   │  │(if MongoDB)│
└─────────────┘  └───────────┘
```

## 8. Search Flow: Query Processing

### CKAN Backend
```
Service: package_search(q="climate change")
    ↓
CKANRepository.package_search()
    ↓
ckan.action.package_search(
    q="climate change",
    fq_list=["organization:research"],
    rows=100
)
    ↓
Solr Search Engine
    ├─ Full-text search on indexed fields
    ├─ Scoring and ranking
    ├─ Filter by organization
    └─ Pagination
    ↓
CKAN Response:
{
    "count": 42,
    "results": [
        {
            "id": "...",
            "name": "...",
            "title": "Climate Study",
            "resources": [...],
            "organization": {...}
        },
        ...
    ]
}
    ↓
Service: Transform to DataSourceResponse
    ↓
Route: Return to Client
```

### MongoDB Backend
```
Service: package_search(q="climate change")
    ↓
MongoDBRepository.package_search()
    ↓
Parse query and filters
    ├─ q="climate change" 
    │  → MongoDB query with $or on regex
    └─ fq_list=["organization:research"]
       → Add to query: {"organization": "research"}
    ↓
MongoDB Query:
db.packages.find({
    "$or": [
        {"title": {"$regex": "climate change", "$options": "i"}},
        {"notes": {"$regex": "climate change", "$options": "i"}},
        {"name": {"$regex": "climate change", "$options": "i"}}
    ],
    "organization": "research"
})
    ↓
Apply sorting, skip, limit
    ↓
MongoDB Response:
{
    "count": 12,
    "results": [
        {
            "id": "...",
            "name": "...",
            "title": "Climate Change Data",
            "resources": [...],
            "organization": {...}
        },
        ...
    ]
}
    ↓
Service: Transform to DataSourceResponse
    ↓
Route: Return to Client
```

## 9. Service Layer Patterns

### Pattern 1: Direct Repository Usage
```python
def get_organization(org_id: str, server: str = "local"):
    repository = catalog_settings.get_repository_by_name(server)
    return repository.organization_show(id=org_id)
```

### Pattern 2: Complex Business Logic
```python
def create_dataset_with_validation(data: DatasetRequest):
    repository = catalog_settings.local_catalog
    
    # Validate organization exists
    try:
        repository.organization_show(id=data.owner_org)
    except:
        raise ValueError("Organization not found")
    
    # Create package
    package = repository.package_create(**data.dict())
    
    # Create resources
    for resource in data.resources:
        repository.resource_create(
            package_id=package["id"],
            **resource.dict()
        )
    
    return package["id"]
```

### Pattern 3: Multi-Backend Search
```python
async def search_across_servers(query: str):
    results = {}
    
    for server in ["local", "global"]:
        repo = catalog_settings.get_repository_by_name(server)
        results[server] = repo.package_search(q=query, rows=100)
    
    return results
```

## 10. Error Handling Flow

```
┌─────────────┐
│HTTP Request │
└──────┬──────┘
       │
    ┌──▼────────────────┐
    │ Try Block         │
    ├──────────────────┤
    │ 1. Get Repository│
    │ 2. Call Service  │
    │ 3. Return Result │
    └──┬─────────────┬──┘
       │             │
       │ ┌──────────▼──────────┐
       │ │ Exception Occurs    │
       │ │ (in service/repo)   │
       │ └──────────┬──────────┘
       │            │
    ┌──▼────────────▼──────────┐
    │ Except Handlers           │
    ├───────────────────────────┤
    │ ValueError → 400 Bad Req  │
    │ NotFound → 404 Not Found  │
    │ ValidationError → 409     │
    │ Generic → 500 Server Err  │
    └──────────┬────────────────┘
               │
    ┌──────────▼──────────┐
    │ HTTPException       │
    │ (with status_code & │
    │  detail message)    │
    └──────────┬──────────┘
               │
    ┌──────────▼────────────┐
    │ JSON Error Response   │
    │ {                     │
    │  "detail": "message"  │
    │ }                     │
    └───────────────────────┘
```

## 11. Index Strategy

### CKAN (Solr)
```
Solr Index:
- Full-text fields: title, notes, name
- Exact match fields: id, name, owner_org
- Facet fields: organization, tags, format
- Sorting: score, metadata_modified
- Real-time indexing
```

### MongoDB
```
Indexes Created:
- packages.name (unique)
- packages.owner_org
- packages.title + packages.notes (text index)
- resources.package_id
- organizations.name (unique)
```

## 12. Deployment Scenarios

### Scenario 1: Development Setup
```
┌─────────────┐
│  Docker Dev │
├─────────────┤
│             │
│ FastAPI App │──────┐
│             │      │
└─────────────┘      │
                     │
                  ┌──▼──────┐
                  │ MongoDB  │
                  │(embedded)│
                  └──────────┘
                  
Configuration:
LOCAL_CATALOG_BACKEND=mongodb
Minimal infrastructure needed
```

### Scenario 2: Production Setup
```
┌──────────────┐
│  K8s Cluster │
├──────────────┤
│              │
│ FastAPI Pods │──────┐
│  (replicas)  │      │
│              │      │
└──────────────┘      │
                   ┌──▼───────┐
                   │ CKAN      │
                   ├───────────┤
                   │ Solr      │
                   ├───────────┤
                   │ PostgreSQL│
                   └───────────┘
                   
Configuration:
LOCAL_CATALOG_BACKEND=ckan
HA setup with replicas
Separate search (Solr)
Persistent storage
```

---

This document provides visual references for understanding the architecture. Refer to `repository-pattern-architecture.md` for detailed explanations.
