"""An unset PRE_CKAN_ORGANIZATION explains itself (issue #274)."""

from unittest.mock import MagicMock, patch

import pytest

from api.services.dataset_services.publish_dataset import (
    _empty_organization_hint,
    publish_dataset_to_preckan,
)

DENIED = (
    "{'__type': 'Authorization Error', 'message': 'Access denied: User "
    "staging_publisher not authorized to add dataset to this organization'}"
)


class TestEmptyOrganizationHint:
    """The explanation appended to a refused write."""

    @patch("api.services.dataset_services.publish_dataset.ckan_settings")
    def test_an_authorization_failure_is_explained(self, settings):
        settings.pre_ckan_organization = ""

        hint = _empty_organization_hint(DENIED, {"owner_org": "services"})

        assert "PRE_CKAN_ORGANIZATION is not set" in hint
        assert "'services'" in hint

    @patch("api.services.dataset_services.publish_dataset.ckan_settings")
    def test_nothing_is_added_when_the_setting_is_configured(self, settings):
        """A refusal then means something else, and guessing would mislead."""
        settings.pre_ckan_organization = "ndp-staging"

        assert _empty_organization_hint(DENIED, {"owner_org": "services"}) == ""

    @patch("api.services.dataset_services.publish_dataset.ckan_settings")
    def test_nothing_is_added_to_an_unrelated_failure(self, settings):
        settings.pre_ckan_organization = ""

        hint = _empty_organization_hint(
            "Internal Server Error", {"owner_org": "services"}
        )

        assert hint == ""

    @pytest.mark.parametrize(
        "message",
        [
            "Access denied: User x not authorized",
            "{'__type': 'Authorization Error'}",
            "User x is not authorized to create packages",
        ],
    )
    @patch("api.services.dataset_services.publish_dataset.ckan_settings")
    def test_the_shapes_ckan_refuses_with_are_recognised(self, settings, message):
        settings.pre_ckan_organization = ""

        assert _empty_organization_hint(message, {"owner_org": "services"}) != ""


class TestPublishSurfacesTheHint:
    """The message the caller actually receives."""

    @staticmethod
    def _publish(pre_ckan_organization):
        local = MagicMock()
        # Publishing resolves the local organization's name before sending,
        # so the stub has to answer with one for the hint to quote it.
        local.organization_show.return_value = {"name": "services"}
        local.package_show.return_value = {
            "id": "pkg-1",
            "name": "a-dataset",
            "title": "A dataset",
            "owner_org": "services",
            "extras": [],
        }
        pre = MagicMock()
        pre.package_create.side_effect = Exception(DENIED)

        with (
            patch(
                "api.services.dataset_services.publish_dataset.ckan_settings"
            ) as settings,
            patch(
                "api.services.dataset_services.publish_dataset.catalog_settings"
            ) as catalog,
            patch(
                "api.services.dataset_services.publish_dataset.CKANRepository"
            ) as repo_cls,
        ):
            settings.pre_ckan_enabled = True
            settings.pre_ckan_organization = pre_ckan_organization
            catalog.local_catalog = local
            repo_cls.return_value = pre
            with pytest.raises(Exception) as raised:
                publish_dataset_to_preckan(dataset_id="pkg-1", user_info={"sub": "s"})
        return str(raised.value)

    # The bug this guards: an Endpoint in the field reported PRE-CKAN as
    # connected and refused every publish, and the error named a user and an
    # organization the operator had never chosen.
    def test_an_unset_organization_is_named_in_the_error(self):
        message = self._publish("")

        assert "Access denied" in message
        assert "PRE_CKAN_ORGANIZATION is not set" in message
        assert "'services'" in message

    def test_a_configured_organization_leaves_the_error_alone(self):
        message = self._publish("ndp-staging")

        assert "Access denied" in message
        assert "PRE_CKAN_ORGANIZATION" not in message


class TestReadinessReportsTheSetting:
    """`GET /ready` says whether the staging organization is configured."""

    @staticmethod
    def _check(organization):
        from api.routes.health_routes.ready import _check_pre_ckan

        with (
            patch("api.routes.health_routes.ready.ckan_settings") as settings,
            patch("api.routes.health_routes.ready.catalog_settings") as catalog,
        ):
            settings.pre_ckan_enabled = True
            settings.pre_ckan_url = "https://staging.example"
            settings.pre_ckan_api_key = "key"
            settings.pre_ckan_organization = organization
            catalog.pre_catalog.check_health.return_value = True
            return _check_pre_ckan()

    @pytest.mark.parametrize(
        "organization,expected", [("ndp-staging", True), ("", False)]
    )
    def test_the_setting_is_reported(self, organization, expected):
        assert self._check(organization)["organization_configured"] is expected

    def test_an_unset_organization_is_not_a_failure(self):
        """
        Deployments whose staging catalog holds the same organizations
        publish fine without it, so this must not read as broken.
        """
        assert self._check("")["status"] != "down"
