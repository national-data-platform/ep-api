# api/services/kafka_services/update_kafka.py

import json
from typing import Optional

from api.config.ckan_settings import ckan_settings

RESERVED_KEYS = {
    "name",
    "title",
    "owner_org",
    "notes",
    "id",
    "resources",
    "collection",
    "host",
    "port",
    "topic",
    "mapping",
    "processing",
}


def update_kafka(
    dataset_id: str,
    dataset_name: Optional[str] = None,
    dataset_title: Optional[str] = None,
    owner_org: Optional[str] = None,
    kafka_topic: Optional[str] = None,
    kafka_host: Optional[str] = None,
    kafka_port: Optional[str] = None,
    dataset_description: Optional[str] = None,
    extras: Optional[dict] = None,
    mapping: Optional[dict] = None,
    processing: Optional[dict] = None,
    ckan_instance=None,
):
    """
    Update a Kafka dataset on CKAN (full replacement).
    If ckan_instance is None, defaults to ckan_settings.ckan.
    """
    if ckan_instance is None:
        ckan_instance = ckan_settings.ckan

    try:
        # Fetch the existing dataset
        dataset = ckan_instance.action.package_show(id=dataset_id)
    except Exception as e:
        raise Exception(f"Error fetching Kafka dataset: {str(e)}")

    # Preserve all existing fields unless new values are provided
    dataset["name"] = dataset_name or dataset.get("name")
    dataset["title"] = dataset_title or dataset.get("title")
    dataset["owner_org"] = owner_org or dataset.get("owner_org")
    dataset["notes"] = dataset_description or dataset.get("notes")

    # Merge current extras with new extras
    current_extras = {
        extra["key"]: extra["value"] for extra in dataset.get("extras", [])
    }

    if extras:
        if RESERVED_KEYS.intersection(extras):
            raise KeyError(
                "Extras contain reserved keys: " f"{RESERVED_KEYS.intersection(extras)}"
            )
        current_extras.update(extras)

    # Update mapping, processing, and Kafka-specific extras
    if mapping:
        current_extras["mapping"] = json.dumps(mapping)
    if processing:
        current_extras["processing"] = json.dumps(processing)
    if kafka_host or kafka_port or kafka_topic:
        current_extras["host"] = kafka_host or current_extras.get("host")
        current_extras["port"] = kafka_port or current_extras.get("port")
        current_extras["topic"] = kafka_topic or current_extras.get("topic")

    # Convert updated extras back to CKAN format
    dataset["extras"] = [{"key": k, "value": v} for k, v in current_extras.items()]

    try:
        updated_dataset = ckan_instance.action.package_update(**dataset)
    except Exception as e:
        raise Exception(f"Error updating Kafka dataset: {str(e)}")

    return updated_dataset["id"]


def patch_kafka(
    dataset_id: str,
    dataset_name: Optional[str] = None,
    dataset_title: Optional[str] = None,
    owner_org: Optional[str] = None,
    kafka_topic: Optional[str] = None,
    kafka_host: Optional[str] = None,
    kafka_port: Optional[str] = None,
    dataset_description: Optional[str] = None,
    extras: Optional[dict] = None,
    mapping: Optional[dict] = None,
    processing: Optional[dict] = None,
    ckan_instance=None,
):
    """
    Partially update a Kafka dataset on CKAN.
    
    Only updates the fields that are provided, leaving others unchanged.
    If ckan_instance is None, defaults to ckan_settings.ckan.
    """
    if ckan_instance is None:
        ckan_instance = ckan_settings.ckan

    try:
        # Fetch the existing dataset
        dataset = ckan_instance.action.package_show(id=dataset_id)
    except Exception as e:
        raise Exception(f"Error fetching Kafka dataset: {str(e)}")

    # Update fields with new values if provided
    if dataset_name is not None:
        dataset["name"] = dataset_name
    if dataset_title is not None:
        dataset["title"] = dataset_title
    if owner_org is not None:
        dataset["owner_org"] = owner_org
    if dataset_description is not None:
        dataset["notes"] = dataset_description

    # Handle extras - merge with existing if provided
    current_extras = {
        extra["key"]: extra["value"] for extra in dataset.get("extras", [])
    }

    if extras:
        if RESERVED_KEYS.intersection(extras):
            raise KeyError(
                "Extras contain reserved keys: " f"{RESERVED_KEYS.intersection(extras)}"
            )
        current_extras.update(extras)

    # Update mapping, processing, and Kafka-specific extras if provided
    if mapping is not None:
        current_extras["mapping"] = json.dumps(mapping)
    if processing is not None:
        current_extras["processing"] = json.dumps(processing)
    
    # Update Kafka-specific extras if provided
    if kafka_host is not None:
        current_extras["host"] = kafka_host
    if kafka_port is not None:
        current_extras["port"] = kafka_port
    if kafka_topic is not None:
        current_extras["topic"] = kafka_topic

    # Convert updated extras back to CKAN format
    dataset["extras"] = [{"key": k, "value": v} for k, v in current_extras.items()]

    try:
        updated_dataset = ckan_instance.action.package_update(**dataset)
    except Exception as e:
        raise Exception(f"Error updating Kafka dataset: {str(e)}")

    return updated_dataset["id"]
