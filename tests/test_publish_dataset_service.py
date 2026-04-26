# tests/test_publish_dataset_service.py
"""
Tests for publish_dataset_to_preckan service, focusing on the
``status=submitted`` extra written to both the Pre-CKAN copy and the
original local dataset.
"""

from unittest.mock import MagicMock, patch

import pytest

from api.services.dataset_services.publish_dataset import (
    SUBMITTED_STATUS_EXTRA,
    _with_submitted_status,
    publish_dataset_to_preckan,
)


class TestWithSubmittedStatus:
    """Helper that produces an extras list carrying status=submitted."""

    def test_none_input_returns_only_status(self):
        result = _with_submitted_status(None)
        assert result == [SUBMITTED_STATUS_EXTRA]

    def test_empty_list_returns_only_status(self):
        result = _with_submitted_status([])
        assert result == [SUBMITTED_STATUS_EXTRA]

    def test_preserves_other_extras(self):
        existing = [
            {"key": "ndp_user_id", "value": "abc123"},
            {"key": "ndp_group_id", "value": "my-org"},
        ]
        result = _with_submitted_status(existing)
        assert {"key": "ndp_user_id", "value": "abc123"} in result
        assert {"key": "ndp_group_id", "value": "my-org"} in result
        assert SUBMITTED_STATUS_EXTRA in result
        assert len(result) == 3

    def test_replaces_existing_status_entry(self):
        existing = [
            {"key": "status", "value": "approved"},
            {"key": "ndp_user_id", "value": "abc123"},
        ]
        result = _with_submitted_status(existing)
        status_entries = [e for e in result if e.get("key") == "status"]
        assert status_entries == [SUBMITTED_STATUS_EXTRA]
        assert {"key": "ndp_user_id", "value": "abc123"} in result

    def test_does_not_mutate_input(self):
        existing = [{"key": "status", "value": "approved"}]
        original_snapshot = [dict(item) for item in existing]
        _with_submitted_status(existing)
        assert existing == original_snapshot


def _build_mocks(
    monkeypatch_settings_path="api.services.dataset_services.publish_dataset",
    pre_ckan_enabled=True,
    pre_ckan_organization=None,
    local_dataset=None,
    package_create_side_effect=None,
    package_patch_side_effect=None,
):
    """Build the standard mock setup used by the publish tests."""
    local_repo = MagicMock(name="local_repo")
    local_repo.package_show.return_value = local_dataset or {
        "id": "local-id-1",
        "name": "my-dataset",
        "title": "My Dataset",
        "owner_org": "my-org",
        "extras": [],
        "resources": [],
    }
    if package_patch_side_effect is not None:
        local_repo.package_patch.side_effect = package_patch_side_effect

    preckan_repo = MagicMock(name="preckan_repo")
    if package_create_side_effect is not None:
        preckan_repo.package_create.side_effect = package_create_side_effect
    else:
        preckan_repo.package_create.return_value = {"id": "preckan-id-1"}

    return local_repo, preckan_repo


class TestPublishDatasetToPreckan:
    """End-to-end behaviour of the publish service."""

    @patch("api.services.dataset_services.publish_dataset.CKANRepository")
    @patch("api.services.dataset_services.publish_dataset.ckan_settings")
    @patch("api.services.dataset_services.publish_dataset.catalog_settings")
    def test_pre_ckan_disabled_raises(
        self,
        mock_catalog_settings,
        mock_ckan_settings,
        mock_ckan_repo_cls,
    ):
        mock_ckan_settings.pre_ckan_enabled = False

        with pytest.raises(ValueError, match="PRE-CKAN is disabled"):
            publish_dataset_to_preckan(dataset_id="any")

        mock_ckan_repo_cls.assert_not_called()

    @patch("api.services.dataset_services.publish_dataset.CKANRepository")
    @patch("api.services.dataset_services.publish_dataset.ckan_settings")
    @patch("api.services.dataset_services.publish_dataset.catalog_settings")
    def test_dataset_not_found_raises(
        self,
        mock_catalog_settings,
        mock_ckan_settings,
        mock_ckan_repo_cls,
    ):
        mock_ckan_settings.pre_ckan_enabled = True
        mock_ckan_settings.pre_ckan_organization = None

        local_repo = MagicMock()
        local_repo.package_show.side_effect = Exception("Not found")
        mock_catalog_settings.local_catalog = local_repo
        mock_ckan_repo_cls.return_value = MagicMock()

        with pytest.raises(ValueError, match="Dataset not found"):
            publish_dataset_to_preckan(dataset_id="missing")

    @patch("api.services.dataset_services.publish_dataset.CKANRepository")
    @patch("api.services.dataset_services.publish_dataset.ckan_settings")
    @patch("api.services.dataset_services.publish_dataset.catalog_settings")
    def test_successful_publish_sets_status_in_both_catalogs(
        self,
        mock_catalog_settings,
        mock_ckan_settings,
        mock_ckan_repo_cls,
    ):
        mock_ckan_settings.pre_ckan_enabled = True
        mock_ckan_settings.pre_ckan_organization = "preckan-org"

        local_repo, preckan_repo = _build_mocks(
            local_dataset={
                "id": "local-id-1",
                "name": "my-dataset",
                "title": "My Dataset",
                "owner_org": "my-org",
                "extras": [
                    {"key": "ndp_user_id", "value": "user-hash"},
                    {"key": "ndp_group_id", "value": "my-org"},
                ],
                "resources": [],
            },
        )
        mock_catalog_settings.local_catalog = local_repo
        mock_ckan_repo_cls.return_value = preckan_repo

        result = publish_dataset_to_preckan(dataset_id="my-dataset")

        assert result == "preckan-id-1"

        # Pre-CKAN copy carries status=submitted alongside existing extras
        preckan_extras = preckan_repo.package_create.call_args.kwargs["extras"]
        assert SUBMITTED_STATUS_EXTRA in preckan_extras
        assert {"key": "ndp_user_id", "value": "user-hash"} in preckan_extras
        assert {"key": "ndp_group_id", "value": "my-org"} in preckan_extras

        # Local dataset is patched with the same submitted status
        local_repo.package_patch.assert_called_once()
        patch_kwargs = local_repo.package_patch.call_args.kwargs
        assert patch_kwargs["id"] == "my-dataset"
        assert SUBMITTED_STATUS_EXTRA in patch_kwargs["extras"]
        assert {"key": "ndp_user_id", "value": "user-hash"} in patch_kwargs["extras"]

    @patch("api.services.dataset_services.publish_dataset.CKANRepository")
    @patch("api.services.dataset_services.publish_dataset.ckan_settings")
    @patch("api.services.dataset_services.publish_dataset.catalog_settings")
    def test_republish_replaces_previous_status(
        self,
        mock_catalog_settings,
        mock_ckan_settings,
        mock_ckan_repo_cls,
    ):
        mock_ckan_settings.pre_ckan_enabled = True
        mock_ckan_settings.pre_ckan_organization = None

        local_repo, preckan_repo = _build_mocks(
            local_dataset={
                "id": "local-id-1",
                "name": "my-dataset",
                "title": "My Dataset",
                "owner_org": "my-org",
                "extras": [
                    {"key": "status", "value": "approved"},
                    {"key": "ndp_user_id", "value": "user-hash"},
                ],
                "resources": [],
            },
        )
        # organization_show is consulted when pre_ckan_organization is None
        local_repo.organization_show.return_value = {"name": "my-org"}
        mock_catalog_settings.local_catalog = local_repo
        mock_ckan_repo_cls.return_value = preckan_repo

        publish_dataset_to_preckan(dataset_id="my-dataset")

        # The Pre-CKAN copy must carry exactly one status entry, equal to
        # submitted — the previous "approved" must be gone.
        preckan_extras = preckan_repo.package_create.call_args.kwargs["extras"]
        status_entries = [e for e in preckan_extras if e.get("key") == "status"]
        assert status_entries == [SUBMITTED_STATUS_EXTRA]

        # Same invariant on the local patch
        patch_kwargs = local_repo.package_patch.call_args.kwargs
        local_status_entries = [
            e for e in patch_kwargs["extras"] if e.get("key") == "status"
        ]
        assert local_status_entries == [SUBMITTED_STATUS_EXTRA]

    @patch("api.services.dataset_services.publish_dataset.CKANRepository")
    @patch("api.services.dataset_services.publish_dataset.ckan_settings")
    @patch("api.services.dataset_services.publish_dataset.catalog_settings")
    def test_preckan_failure_leaves_local_untouched(
        self,
        mock_catalog_settings,
        mock_ckan_settings,
        mock_ckan_repo_cls,
    ):
        mock_ckan_settings.pre_ckan_enabled = True
        mock_ckan_settings.pre_ckan_organization = "preckan-org"

        local_repo, preckan_repo = _build_mocks(
            package_create_side_effect=Exception("That name is already in use"),
        )
        mock_catalog_settings.local_catalog = local_repo
        mock_ckan_repo_cls.return_value = preckan_repo

        with pytest.raises(ValueError, match="already exists in PRE-CKAN"):
            publish_dataset_to_preckan(dataset_id="my-dataset")

        local_repo.package_patch.assert_not_called()

    @patch("api.services.dataset_services.publish_dataset.CKANRepository")
    @patch("api.services.dataset_services.publish_dataset.ckan_settings")
    @patch("api.services.dataset_services.publish_dataset.catalog_settings")
    def test_local_patch_failure_does_not_undo_preckan(
        self,
        mock_catalog_settings,
        mock_ckan_settings,
        mock_ckan_repo_cls,
    ):
        mock_ckan_settings.pre_ckan_enabled = True
        mock_ckan_settings.pre_ckan_organization = "preckan-org"

        local_repo, preckan_repo = _build_mocks(
            package_patch_side_effect=Exception("read-only"),
        )
        mock_catalog_settings.local_catalog = local_repo
        mock_ckan_repo_cls.return_value = preckan_repo

        # Should still return the new Pre-CKAN id even though the local
        # patch failed (best-effort mirroring).
        result = publish_dataset_to_preckan(dataset_id="my-dataset")
        assert result == "preckan-id-1"
        local_repo.package_patch.assert_called_once()
