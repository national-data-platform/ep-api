# api/routes/update_routes/patch_kafka.py

from typing import Any, Dict, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status

from api.config import ckan_settings
from api.models.update_kafka_model import KafkaDataSourceUpdateRequest
from api.services import kafka_services
from api.services.auth_services import get_current_user

router = APIRouter()


@router.patch(
    "/kafka/{dataset_id}",
    response_model=dict,
    status_code=status.HTTP_200_OK,
    summary="Partially update an existing Kafka topic",
    description=(
        "Partially update an existing Kafka topic and its associated metadata.\n\n"
        "Only updates the fields that are provided, leaving others "
        "unchanged. This is useful when you only want to modify specific "
        "attributes without affecting the rest of the Kafka dataset.\n\n"
        "### Path Parameters\n"
        "- **dataset_id**: The unique identifier of the Kafka dataset to update\n\n"
        "### Optional Fields (only provide fields to update)\n"
        "- **dataset_name**: The unique name of the dataset.\n"
        "- **dataset_title**: The title of the dataset.\n"
        "- **owner_org**: The ID of the organization.\n"
        "- **kafka_topic**: The Kafka topic name.\n"
        "- **kafka_host**: The Kafka host.\n"
        "- **kafka_port**: The Kafka port.\n"
        "- **dataset_description**: A description of the dataset.\n"
        "- **extras**: Additional metadata (will be merged with existing).\n"
        "- **mapping**: Mapping information.\n"
        "- **processing**: Processing information.\n\n"
        "### Query Parameter\n"
        "Use `?server=local` or `?server=pre_ckan` to pick the CKAN instance. "
        "Defaults to 'local' if not provided.\n\n"
        "### Example Payload (partial update)\n"
        "{\n"
        '    "kafka_host": "new-kafka.example.com",\n'
        '    "extras": {\n'
        '        "version": "2.1",\n'
        '        "last_updated": "2024-01-15"\n'
        "    }\n"
        "}\n"
        "Note: Only `kafka_host` and `extras` will be updated. All other "
        "fields remain unchanged, and the new extras will be merged with "
        "existing ones.\n"
    ),
    responses={
        200: {
            "description": "Kafka dataset partially updated successfully",
            "content": {
                "application/json": {
                    "example": {"message": "Kafka dataset updated successfully"}
                }
            },
        },
        400: {
            "description": "Bad Request",
            "content": {
                "application/json": {
                    "example": {"detail": "Error updating Kafka dataset: <error>"}
                }
            },
        },
        404: {
            "description": "Not Found",
            "content": {
                "application/json": {"example": {"detail": "Kafka dataset not found"}}
            },
        },
    },
)
async def patch_kafka_datasource(
    dataset_id: str,
    data: KafkaDataSourceUpdateRequest,
    server: Literal["local", "pre_ckan"] = Query(
        "local", description="Choose 'local' or 'pre_ckan'. Defaults to 'local'."
    ),
    _: Dict[str, Any] = Depends(get_current_user),
):
    """
    Partially update a Kafka dataset by dataset_id.
    
    Only updates the fields that are provided in the request, leaving all
    other fields unchanged. This is ideal for making small updates without
    needing to provide the complete Kafka dataset information.

    Parameters
    ----------
    dataset_id : str
        The unique identifier of the Kafka dataset to patch.
    data : KafkaDataSourceUpdateRequest
        The partial Kafka dataset update information.
    server : Literal['local', 'pre_ckan']
        CKAN instance to use. Defaults to 'local'.
    _ : Dict[str, Any]
        Keycloak user auth (unused).

    Returns
    -------
    dict
        A success message indicating the Kafka dataset was updated.

    Raises
    ------
    HTTPException
        - 400: for update errors or invalid server config
        - 404: if Kafka dataset not found
    """
    try:
        if server == "pre_ckan":
            if not ckan_settings.pre_ckan_enabled:
                raise HTTPException(
                    status_code=400, detail="Pre-CKAN is disabled and cannot be used."
                )
            ckan_instance = ckan_settings.pre_ckan
        else:
            ckan_instance = ckan_settings.ckan

        updated_id = kafka_services.patch_kafka(
            dataset_id=dataset_id,
            dataset_name=data.dataset_name,
            dataset_title=data.dataset_title,
            owner_org=data.owner_org,
            kafka_topic=data.kafka_topic,
            kafka_host=data.kafka_host,
            kafka_port=data.kafka_port,
            dataset_description=data.dataset_description,
            extras=data.extras,
            mapping=data.mapping,
            processing=data.processing,
            ckan_instance=ckan_instance,
        )
        
        if not updated_id:
            raise HTTPException(status_code=404, detail="Kafka dataset not found")
            
        return {"message": "Kafka dataset updated successfully"}

    except HTTPException as he:
        raise he
    except Exception as exc:
        error_msg = str(exc)
        if "No scheme supplied" in error_msg:
            raise HTTPException(
                status_code=400,
                detail="Pre-CKAN server is not configured or unreachable.",
            )
        if "not found" in error_msg.lower():
            raise HTTPException(status_code=404, detail="Kafka dataset not found")
        raise HTTPException(
            status_code=400, detail=f"Error updating Kafka dataset: {error_msg}"
        )