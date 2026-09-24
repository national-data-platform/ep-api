"""A refused publish is reported by what went wrong (issue #263)."""

from unittest.mock import MagicMock, patch

import pytest
from ckanapi.errors import NotAuthorized, NotFound, ValidationError

from api.services.dataset_services.publish_dataset import (
    PreCkanPublishError,
    _describe,
    _publish_failure,
)

DATASET = {"owner_org": "services"}


class TestDescribe:
    """The reason has to survive an empty message."""

    # The bug this guards: an authorization refusal with no body reached
    # the user as "Error creating dataset in PRE-CKAN: None".
    def test_a_bare_refusal_is_named_by_its_class(self):
        assert _describe(NotAuthorized()) == "NotAuthorized"

    def test_a_message_is_kept_and_attributed(self):
        described = _describe(ValidationError({"owner_org": ["Missing value"]}))

        assert described.startswith("ValidationError: ")
        assert "Missing value" in described

    def test_an_ordinary_exception_is_described_too(self):
        assert _describe(RuntimeError("connection reset")) == (
            "RuntimeError: connection reset"
        )


class TestStatusFromExceptionType:
    """
    The status comes from the type the catalog raised, not from matching
    English text, so a reworded CKAN message cannot silently demote a
    failure to a generic 500.
    """

    @pytest.mark.parametrize(
        "exc,expected",
        [
            (NotAuthorized(), 403),
            (NotAuthorized({"__type": "Authorization Error"}), 403),
            (ValidationError({"owner_org": ["Missing value"]}), 400),
            (NotFound("nope"), 502),
            (RuntimeError("connection reset"), 502),
        ],
    )
    def test_each_failure_carries_its_status(self, exc, expected):
        assert _publish_failure(exc, DATASET).status_code == expected

    def test_a_refusal_is_not_an_internal_error(self):
        """A wrong staging key is the deployment's problem, not a crash."""
        assert _publish_failure(NotAuthorized(), DATASET).status_code != 500

    @patch("api.services.dataset_services.publish_dataset.ckan_settings")
    def test_the_unset_organization_hint_still_reaches_a_bare_refusal(self, settings):
        """
        The commonest real case: empty PRE_CKAN_ORGANIZATION and a refusal
        whose message is empty. Both explanations have to survive together.
        """
        settings.pre_ckan_organization = ""

        failure = _publish_failure(NotAuthorized(), DATASET)

        assert failure.status_code == 403
        assert "NotAuthorized" in failure.detail
        assert "PRE_CKAN_ORGANIZATION is not set" in failure.detail


class TestRouteAnswersWithThatStatus:
    """The status the caller actually receives."""

    @staticmethod
    def _publish_raising(exc):
        from fastapi import FastAPI
        from fastapi.testclient import TestClient

        from api.routes.register_routes.publish_dataset import router
        from api.services.auth_services import get_current_user

        app = FastAPI()
        app.include_router(router)
        app.dependency_overrides[get_current_user] = lambda: {
            "roles": ["ndp_admin"],
            "groups": [],
            "sub": "test_user",
            "username": "Test User",
        }
        from api.config.swagger_settings import swagger_settings

        with (
            patch(
                "api.routes.register_routes.publish_dataset.publish_dataset_to_preckan"
            ) as publish,
            patch.object(swagger_settings, "enable_group_based_access", False),
        ):
            publish.side_effect = exc
            return TestClient(app).post(
                "/dataset/pkg-1/publish",
                json={},
                headers={"Authorization": "Bearer testing_token"},
            )

    def test_a_refusal_answers_403(self):
        response = self._publish_raising(
            PreCkanPublishError("Error creating dataset in PRE-CKAN: X", 403)
        )

        assert response.status_code == 403
        assert "PRE-CKAN" in response.json()["detail"]

    def test_an_unreachable_catalog_answers_502(self):
        response = self._publish_raising(
            PreCkanPublishError("Error creating dataset in PRE-CKAN: Y", 502)
        )

        assert response.status_code == 502

    def test_an_unexpected_failure_is_still_500(self):
        """Only genuinely unknown failures stay an internal error."""
        response = self._publish_raising(RuntimeError("boom"))

        assert response.status_code == 500


class TestNameCollisionStillRetries:
    """The one branch that must keep matching on CKAN's wording."""

    def test_a_taken_name_is_republished_with_a_suffix(self):
        from api.services.dataset_services.publish_dataset import (
            publish_dataset_to_preckan,
        )

        local = MagicMock()
        local.organization_show.return_value = {"name": "services"}
        local.package_show.return_value = {
            "id": "pkg-1",
            "name": "a-dataset",
            "title": "A dataset",
            "owner_org": "services",
            "extras": [],
        }
        pre = MagicMock()
        pre.package_create.side_effect = [
            ValidationError({"name": ["That URL is already in use."]}),
            {"id": "new-1", "name": "a-dataset-x", "title": "A dataset (x)"},
        ]

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
            settings.pre_ckan_organization = "ndp-staging"
            catalog.local_catalog = local
            repo_cls.return_value = pre
            result = publish_dataset_to_preckan(
                dataset_id="pkg-1", user_info={"sub": "s"}
            )

        assert result["id"] == "new-1"
        assert "already exists in PRE-CKAN" in result["warning"]
        assert pre.package_create.call_count == 2
