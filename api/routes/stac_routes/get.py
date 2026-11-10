# api/routes/stac_routes/get.py
"""Read-only summaries of STAC collection resources (issue #405)."""

from typing import Any, Dict, Literal

from fastapi import APIRouter, Query

from api.services import stac_services

router = APIRouter()

_SERVER = Query(
    "global", description="The catalog that holds the dataset: 'local' or 'global'."
)
_DATASET = Query(..., description="The dataset's id or name.")
_RESOURCE = Query(..., description="The id of the resource that is the collection.")


@router.get(
    "/stac/collection",
    response_model=dict,
    summary="Summarise a STAC collection resource",
    description=(
        "Reads the STAC collection a resource of a public dataset points to "
        "and returns its title, description, license, spatial and temporal "
        "extent, summaries, and its items (absolute links). Only the "
        "resource's own URL is read. 404 when the dataset or resource does "
        "not exist, is private, or STAC_SUMMARY_ENABLED is false; 422 when "
        "the resource is not a STAC collection; 502 when it cannot be read."
    ),
)
def get_stac_collection(
    dataset_id: str = _DATASET,
    resource_id: str = _RESOURCE,
    server: Literal["local", "global"] = _SERVER,
) -> Dict[str, Any]:
    return stac_services.get_collection_summary(server, dataset_id, resource_id)


@router.get(
    "/stac/item",
    response_model=dict,
    summary="Summarise one item of a STAC collection resource",
    description=(
        "Returns one item's period, properties and assets (download links). "
        "`href` must be one of the item links /stac/collection returned for "
        "the same resource; any other URL is refused with 404."
    ),
)
def get_stac_item(
    dataset_id: str = _DATASET,
    resource_id: str = _RESOURCE,
    href: str = Query(..., description="The item's absolute URL."),
    server: Literal["local", "global"] = _SERVER,
) -> Dict[str, Any]:
    return stac_services.get_item_summary(server, dataset_id, resource_id, href)
