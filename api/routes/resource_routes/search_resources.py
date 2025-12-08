# api/routes/resource_routes/search_resources.py
"""
Resource search endpoint.

Allows searching for resources across all datasets with various filters.
"""

from typing import Literal, Optional

from fastapi import APIRouter, HTTPException, Query

from api.config import ckan_settings
from api.repositories import CKANRepository
from api.services import dataset_services

router = APIRouter()


@router.get(
    "/resources/search",
    response_model=dict,
    summary="Search resources",
    description=(
        "Search for resources across all datasets.\n\n"
        "Returns only resources matching the criteria, not full datasets.\n\n"
        "### Filter Options\n"
        "- **q**: General search query (searches name, url, description)\n"
        "- **name**: Filter by resource name (partial match)\n"
        "- **url**: Filter by resource URL (partial match)\n"
        "- **format**: Filter by format (CSV, JSON, S3, etc.)\n"
        "- **description**: Filter by description (partial match)\n\n"
        "### Pagination\n"
        "- **limit**: Maximum results to return (default: 100)\n"
        "- **offset**: Number of results to skip\n\n"
        "### Response\n"
        "Each resource includes parent dataset context:\n"
        "- `dataset_id`: Parent dataset ID\n"
        "- `dataset_name`: Parent dataset name\n"
        "- `dataset_title`: Parent dataset title"
    ),
    responses={
        200: {
            "description": "Search results",
            "content": {
                "application/json": {
                    "example": {
                        "count": 2,
                        "results": [
                            {
                                "id": "res-123",
                                "name": "data.csv",
                                "url": "https://example.com/data.csv",
                                "format": "CSV",
                                "description": "Sample data file",
                                "dataset_id": "ds-456",
                                "dataset_name": "my-dataset",
                                "dataset_title": "My Dataset",
                            }
                        ],
                    }
                }
            },
        },
        400: {
            "description": "Bad Request",
            "content": {
                "application/json": {
                    "example": {"detail": "Error searching resources: <error message>"}
                }
            },
        },
    },
)
async def search_resources_endpoint(
    q: Optional[str] = Query(
        None, description="General search query (searches name, url, description)"
    ),
    name: Optional[str] = Query(None, description="Filter by resource name"),
    url: Optional[str] = Query(None, description="Filter by resource URL"),
    format: Optional[str] = Query(
        None, description="Filter by format (CSV, JSON, S3, kafka, etc.)"
    ),
    description: Optional[str] = Query(None, description="Filter by description"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum results to return"),
    offset: int = Query(0, ge=0, description="Number of results to skip"),
    server: Literal["local", "pre_ckan"] = Query(
        "local", description="Choose 'local' or 'pre_ckan'. Defaults to 'local'."
    ),
):
    """
    Search for resources matching the given criteria.

    Parameters
    ----------
    q : str, optional
        General search query
    name : str, optional
        Filter by resource name
    url : str, optional
        Filter by resource URL
    format : str, optional
        Filter by format
    description : str, optional
        Filter by description
    limit : int
        Maximum results to return
    offset : int
        Results to skip for pagination
    server : str
        Which catalog to use
    """
    try:
        repository = None
        if server == "pre_ckan":
            if not ckan_settings.pre_ckan_enabled:
                raise HTTPException(
                    status_code=400, detail="Pre-CKAN is disabled and cannot be used."
                )
            repository = CKANRepository(ckan_settings.pre_ckan)

        result = dataset_services.search_resources(
            query=q,
            name=name,
            url=url,
            format=format,
            description=description,
            limit=limit,
            offset=offset,
            repository=repository,
        )
        return result

    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(
            status_code=400, detail=f"Error searching resources: {str(e)}"
        )
