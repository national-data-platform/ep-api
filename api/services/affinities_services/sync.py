# api/services/affinities_services/sync.py
"""
Keep Affinities in step with the catalog (issues #279 and #280).

Every route that creates, changes or deletes a dataset or a service calls
one of the two functions here, so Affinities always describes what the
Endpoint currently holds:

- :func:`sync_with_affinities` after a create or an update. A dataset or
  service with an ``ndp_affinity_uuid`` extra has its record in Affinities
  replaced with its current title and metadata. One without it (registered
  before this sync existed, or through a route that did not register) is
  registered, and the UUID Affinities returns is stored on it. If Affinities
  no longer has the record, it is registered again.
- :func:`forget_in_affinities` after a delete. The record is deleted, and
  Affinities deletes its relationship with the Endpoint and its triple with
  it. A dataset deleted in CKAN is only marked deleted there, but it is gone
  for every reader of the Endpoint, so it counts as deleted here too.

Neither ever fails the request: Affinities is an index next to the catalog,
and a problem reaching it is logged, as registration always did.
"""

import logging
from typing import Any

from api.config.catalog_settings import catalog_settings
from api.repositories import CKANRepository
from api.services.affinities_services.affinities_client import AffinitiesClient

logger = logging.getLogger(__name__)

AFFINITY_UUID_EXTRA = "ndp_affinity_uuid"

# Services are catalog datasets of this organization (see add_service).
SERVICES_ORGANIZATION = "services"


def resolve_repository(repository=None, ckan_instance=None):
    """
    Return the catalog a route wrote to.

    The routes hold either a repository or, for the older services, the
    CKAN instance of the pre-CKAN server (``None`` meaning the local
    catalog). Both are accepted so each route can pass what it has.
    """
    if repository is not None:
        return repository
    if ckan_instance is not None:
        return CKANRepository(ckan_instance)
    return catalog_settings.local_catalog


def fetch_dataset(dataset_id: str, repository=None, ckan_instance=None):
    """
    Read a dataset before it is deleted, for :func:`forget_in_affinities`.

    Returns
    -------
    dict or None
        The dataset, or None when it cannot be read (it does not exist, or
        the catalog failed); the delete then goes ahead as before.
    """
    try:
        repo = resolve_repository(repository, ckan_instance)
        return with_organization_name(repo.package_show(id=dataset_id), repo)
    except Exception as exc:
        logger.debug(f"Could not read dataset {dataset_id} before delete: {exc}")
        return None


def _extras(dataset: dict[str, Any]) -> dict[str, Any]:
    extras = dataset.get("extras") or []
    if isinstance(extras, dict):
        return extras
    return {item.get("key"): item.get("value") for item in extras}


def _organization(dataset: dict[str, Any]) -> str | None:
    organization = dataset.get("organization")
    if isinstance(organization, dict) and organization.get("name"):
        return organization["name"]
    return dataset.get("owner_org")


def with_organization_name(dataset: dict[str, Any], repo) -> dict[str, Any]:
    """
    Make sure the dataset names its organization.

    CKAN returns the organization with the dataset; the MongoDB catalog
    returns only ``owner_org``, the organization's id, and the name is what
    tells a service from a dataset and what registration always sent.
    """
    organization = dataset.get("organization")
    if isinstance(organization, dict) and organization.get("name"):
        return dataset
    owner_org = dataset.get("owner_org")
    if not owner_org or repo is None:
        return dataset
    try:
        found = repo.organization_show(id=owner_org)
    except Exception as exc:
        logger.debug(f"Could not read organization {owner_org}: {exc}")
        return dataset
    if isinstance(found, dict) and found.get("name"):
        dataset = dict(dataset)
        dataset["organization"] = {"name": found["name"]}
    return dataset


def _tags(dataset: dict[str, Any]) -> list[str]:
    tags = []
    for tag in dataset.get("tags") or []:
        tags.append(tag.get("name") if isinstance(tag, dict) else tag)
    return [tag for tag in tags if tag]


def is_service(dataset: dict[str, Any]) -> bool:
    """Tell a registered service from a dataset."""
    return _organization(dataset) == SERVICES_ORGANIZATION


def dataset_record(dataset: dict[str, Any]) -> dict[str, Any]:
    """What Affinities holds for a dataset: the fields registration sent."""
    return {
        "title": dataset.get("title") or dataset.get("name"),
        "metadata": {
            "name": dataset.get("name"),
            "owner_org": _organization(dataset),
            "local_id": dataset.get("id"),
            "notes": dataset.get("notes"),
            "tags": _tags(dataset),
        },
    }


def service_record(dataset: dict[str, Any]) -> dict[str, Any]:
    """What Affinities holds for a service: the fields registration sent."""
    extras = _extras(dataset)
    return {
        "service_type": extras.get("service_type"),
        "openapi_url": extras.get("documentation_url"),
        "metadata": {
            "service_name": dataset.get("name"),
            "service_title": dataset.get("title"),
            "service_url": extras.get("service_url"),
            "local_id": dataset.get("id"),
            "notes": dataset.get("notes"),
        },
    }


async def sync_with_affinities(
    dataset_id: str, repository=None, ckan_instance=None
) -> None:
    """
    Register or update a dataset or service in Affinities.

    Parameters
    ----------
    dataset_id : str
        Id (or name) of the dataset or service just created or changed.
    repository, ckan_instance
        The catalog it is in; see :func:`resolve_repository`.
    """
    client = AffinitiesClient()
    if not client.is_enabled:
        return

    try:
        repo = resolve_repository(repository, ckan_instance)
        dataset = with_organization_name(repo.package_show(id=dataset_id), repo)
        await _sync(client, dataset, repo)
    except Exception as exc:
        logger.warning(f"Failed to update Affinities for {dataset_id}: {exc}")


async def _sync(client: AffinitiesClient, dataset: dict[str, Any], repo) -> None:
    service = is_service(dataset)
    uid = _extras(dataset).get(AFFINITY_UUID_EXTRA)

    if uid:
        if service:
            outcome = await client.update_service(uid, **service_record(dataset))
        else:
            outcome = await client.update_dataset(uid, **dataset_record(dataset))
        if outcome != client.MISSING:
            return
        logger.warning(
            f"Affinities no longer has {uid} for {dataset.get('id')}; "
            "registering it again."
        )

    if service:
        new_uid = await client.register_service(**service_record(dataset))
    else:
        new_uid = await client.register_dataset(**dataset_record(dataset))

    if new_uid:
        _store_uuid(dataset, str(new_uid), repo)


def _store_uuid(dataset: dict[str, Any], uid: str, repo) -> None:
    # Imported here: the dataset services import the catalog settings,
    # which import this package.
    from api.services.dataset_services.general_dataset import patch_general_dataset

    try:
        patch_general_dataset(
            dataset_id=dataset["id"],
            extras={AFFINITY_UUID_EXTRA: uid},
            repository=repo,
        )
        logger.info(f"Stored Affinities UUID {uid} in {dataset['id']}")
    except Exception as exc:
        logger.warning(
            f"Failed to store Affinities UUID {uid} in {dataset.get('id')}: {exc}"
        )


async def forget_in_affinities(dataset: dict[str, Any] | None) -> None:
    """
    Delete a dataset's or service's record from Affinities.

    Parameters
    ----------
    dataset : dict or None
        The dataset as read before it was deleted (see
        :func:`fetch_dataset`). Nothing is done without it, or when it was
        never registered.
    """
    if not dataset:
        return

    uid = _extras(dataset).get(AFFINITY_UUID_EXTRA)
    client = AffinitiesClient()
    if not uid or not client.is_enabled:
        return

    try:
        if is_service(dataset):
            outcome = await client.delete_service(uid)
        else:
            outcome = await client.delete_dataset(uid)
        if outcome == client.OK:
            logger.info(f"Deleted {uid} from Affinities ({dataset.get('id')})")
        else:
            logger.warning(
                f"Could not delete {uid} from Affinities ({dataset.get('id')}); "
                "the record stays there."
            )
    except Exception as exc:
        logger.warning(f"Failed to delete {uid} from Affinities: {exc}")
