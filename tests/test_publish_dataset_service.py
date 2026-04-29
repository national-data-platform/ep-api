# tests/test_publish_dataset_service.py
"""
Tests for publish_dataset_to_preckan service, covering both the
``status=submitted`` extra written to both the Pre-CKAN copy and the
original local dataset, and the auto-rename behavior when the dataset
name is already in use in PRE-CKAN.
"""

import re
from datetime import datetime
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

        assert result == {
            "id": "preckan-id-1",
            "name": "my-dataset",
            "title": "My Dataset",
            "warning": None,
        }

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
    def test_duplicate_name_auto_renames_and_publishes(
        self,
        mock_catalog_settings,
        mock_ckan_settings,
        mock_ckan_repo_cls,
    ):
        mock_ckan_settings.pre_ckan_enabled = True
        mock_ckan_settings.pre_ckan_organization = "preckan-org"

        local_repo, preckan_repo = _build_mocks()
        # First call raises duplicate, second call succeeds
        preckan_repo.package_create.side_effect = [
            Exception("That name is already in use"),
            {"id": "preckan-id-renamed"},
        ]
        mock_catalog_settings.local_catalog = local_repo
        mock_ckan_repo_cls.return_value = preckan_repo

        fixed_now = datetime(2026, 4, 29, 17, 0, 0)
        with patch(
            "api.services.dataset_services.publish_dataset.datetime"
        ) as mock_datetime:
            mock_datetime.now.return_value = fixed_now
            mock_datetime.strftime = datetime.strftime

            result = publish_dataset_to_preckan(dataset_id="my-dataset")

        assert result == {
            "id": "preckan-id-renamed",
            "name": "my-dataset-20260429170000",
            "title": "My Dataset (2026-04-29 17:00:00)",
            "warning": (
                "A dataset named 'my-dataset' already exists in PRE-CKAN. "
                "This dataset was published as 'my-dataset-20260429170000' "
                "with title 'My Dataset (2026-04-29 17:00:00)'."
            ),
        }
        # Two attempts: first with the original name, second with the suffix
        assert preckan_repo.package_create.call_count == 2
        retry_kwargs = preckan_repo.package_create.call_args_list[1].kwargs
        assert retry_kwargs["name"] == "my-dataset-20260429170000"
        assert retry_kwargs["title"] == "My Dataset (2026-04-29 17:00:00)"
        # The slug stays valid for CKAN
        assert re.match(r"^[a-z0-9_-]+$", retry_kwargs["name"])
        # Local dataset still gets marked as submitted (publish succeeded)
        local_repo.package_patch.assert_called_once()

    @patch("api.services.dataset_services.publish_dataset.CKANRepository")
    @patch("api.services.dataset_services.publish_dataset.ckan_settings")
    @patch("api.services.dataset_services.publish_dataset.catalog_settings")
    def test_duplicate_url_also_auto_renames(
        self,
        mock_catalog_settings,
        mock_ckan_settings,
        mock_ckan_repo_cls,
    ):
        mock_ckan_settings.pre_ckan_enabled = True
        mock_ckan_settings.pre_ckan_organization = "preckan-org"

        local_repo, preckan_repo = _build_mocks()
        preckan_repo.package_create.side_effect = [
            Exception("That URL is already in use"),
            {"id": "preckan-id-2"},
        ]
        mock_catalog_settings.local_catalog = local_repo
        mock_ckan_repo_cls.return_value = preckan_repo

        result = publish_dataset_to_preckan(dataset_id="my-dataset")

        assert result["id"] == "preckan-id-2"
        assert result["name"].startswith("my-dataset-")
        assert result["title"].startswith("My Dataset (")
        assert result["warning"] is not None
        assert "my-dataset" in result["warning"]
        assert preckan_repo.package_create.call_count == 2

    @patch("api.services.dataset_services.publish_dataset.CKANRepository")
    @patch("api.services.dataset_services.publish_dataset.ckan_settings")
    @patch("api.services.dataset_services.publish_dataset.catalog_settings")
    def test_non_duplicate_failure_leaves_local_untouched(
        self,
        mock_catalog_settings,
        mock_ckan_settings,
        mock_ckan_repo_cls,
    ):
        """
        Non-duplicate Pre-CKAN errors (e.g. transport failures) must NOT
        trigger an auto-rename retry, must propagate, and must leave the
        local dataset untouched (no mirror patch).
        """
        mock_ckan_settings.pre_ckan_enabled = True
        mock_ckan_settings.pre_ckan_organization = "preckan-org"

        local_repo, preckan_repo = _build_mocks(
            package_create_side_effect=Exception("Some other CKAN error"),
        )
        mock_catalog_settings.local_catalog = local_repo
        mock_ckan_repo_cls.return_value = preckan_repo

        with pytest.raises(
            Exception, match="Error creating dataset in PRE-CKAN: Some other CKAN error"
        ):
            publish_dataset_to_preckan(dataset_id="my-dataset")

        # No auto-rename retry happened
        assert preckan_repo.package_create.call_count == 1
        # Local dataset was not marked as submitted
        local_repo.package_patch.assert_not_called()

    @patch("api.services.dataset_services.publish_dataset.CKANRepository")
    @patch("api.services.dataset_services.publish_dataset.ckan_settings")
    @patch("api.services.dataset_services.publish_dataset.catalog_settings")
    def test_organization_missing_still_raises_with_clear_message(
        self,
        mock_catalog_settings,
        mock_ckan_settings,
        mock_ckan_repo_cls,
    ):
        mock_ckan_settings.pre_ckan_enabled = True
        mock_ckan_settings.pre_ckan_organization = "preckan-org"

        local_repo, preckan_repo = _build_mocks(
            package_create_side_effect=Exception(
                "Organization does not exist: preckan-org"
            ),
        )
        mock_catalog_settings.local_catalog = local_repo
        mock_ckan_repo_cls.return_value = preckan_repo

        with pytest.raises(ValueError, match="does not exist in PRE-CKAN"):
            publish_dataset_to_preckan(dataset_id="my-dataset")

        assert preckan_repo.package_create.call_count == 1
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
        assert result["id"] == "preckan-id-1"
        assert result["warning"] is None
        local_repo.package_patch.assert_called_once()
