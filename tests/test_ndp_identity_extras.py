"""The NDP identity extras cannot be set from outside (issue #272)."""

from unittest.mock import MagicMock, patch

import pytest

from api.services.metadata_services import (
    NDP_MANAGED_EXTRAS,
    calculate_md5,
    preserve_ndp_metadata,
)

REAL_HASH = calculate_md5("the-real-creator-sub")
FORGED = "0" * 32


class TestPreserveNdpMetadata:
    """The helper every update path merges through."""

    def test_a_supplied_identity_extra_is_ignored(self):
        merged = preserve_ndp_metadata(
            {"ndp_creator_md5": REAL_HASH}, {"ndp_creator_md5": FORGED}
        )

        assert merged["ndp_creator_md5"] == REAL_HASH

    def test_every_managed_key_is_protected(self):
        current = {key: f"real-{key}" for key in NDP_MANAGED_EXTRAS}
        incoming = {key: "forged" for key in NDP_MANAGED_EXTRAS}

        assert preserve_ndp_metadata(current, incoming) == current

    def test_ordinary_extras_still_update(self):
        merged = preserve_ndp_metadata(
            {"topic": "old", "ndp_user_id": "real"},
            {"topic": "new", "added": "yes"},
        )

        assert merged == {"topic": "new", "added": "yes", "ndp_user_id": "real"}

    def test_a_dataset_without_the_hash_does_not_acquire_one(self):
        """
        Filling it in here would record whoever edited last as the
        creator, which is worse than leaving it absent.
        """
        merged = preserve_ndp_metadata({}, {"ndp_creator_md5": FORGED})

        assert "ndp_creator_md5" not in merged

    def test_missing_arguments_are_tolerated(self):
        assert preserve_ndp_metadata(None, None) == {}
        assert preserve_ndp_metadata({"a": "1"}, None) == {"a": "1"}


def _dataset_with_hash():
    return {
        "id": "pkg-1",
        "name": "existing",
        "title": "Existing",
        "notes": "",
        "owner_org": "services",
        "extras": [
            {"key": "ndp_creator_md5", "value": REAL_HASH},
            {"key": "topic", "value": "old"},
        ],
    }


def _extras_sent_to_ckan(mock_repository):
    """Pull the extras out of the repository call as a mapping."""
    kwargs = mock_repository.package_update.call_args.kwargs
    return {extra["key"]: extra["value"] for extra in kwargs["extras"]}


class TestGeneralDatasetUpdatePaths:
    """
    The route an ordinary caller uses. Before this fix, a plain update
    carrying ndp_creator_md5 replaced the stored hash, so a dataset could
    report a creator who never touched it.
    """

    @pytest.mark.parametrize("action", ["update", "patch"])
    def test_the_stored_hash_survives_a_forgery_attempt(self, action):
        from api.services.dataset_services.general_dataset import (
            patch_general_dataset,
            update_general_dataset,
        )

        repository = MagicMock()
        repository.package_show.return_value = _dataset_with_hash()
        repository.package_update.return_value = {"id": "pkg-1"}
        run = update_general_dataset if action == "update" else patch_general_dataset

        run(
            dataset_id="pkg-1",
            extras={"ndp_creator_md5": FORGED, "topic": "new"},
            repository=repository,
        )

        extras = _extras_sent_to_ckan(repository)
        assert extras["ndp_creator_md5"] == REAL_HASH
        assert extras["topic"] == "new"


class TestUrlDatasetUpdatePath:
    """`PUT /dataset/{id}` for URL-backed datasets."""

    @pytest.mark.asyncio
    async def test_the_stored_hash_survives_a_forgery_attempt(self):
        from api.models.update_dataset_model import DatasetUpdateRequest
        from api.services.url_services.update_dataset import update_dataset

        ckan = MagicMock()
        ckan.action.package_show.return_value = _dataset_with_hash()
        with patch(
            "api.services.url_services.update_dataset.ckan_settings"
        ) as settings:
            settings.ckan = ckan
            await update_dataset(
                "pkg-1",
                DatasetUpdateRequest(
                    extras={"ndp_creator_md5": FORGED, "topic": "new"}
                ),
                ckan_instance=ckan,
            )

        patched = ckan.action.package_patch.call_args.kwargs
        extras = {e["key"]: e["value"] for e in patched["extras"]}
        assert extras["ndp_creator_md5"] == REAL_HASH
        assert extras["topic"] == "new"
