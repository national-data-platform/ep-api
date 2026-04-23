# tests/test_access_request_service.py
"""
Tests for the access-request service layer.
"""

from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException

from api.services.access_request_services import access_request_service


@pytest.fixture
def mock_repo():
    return MagicMock()


@pytest.fixture(autouse=True)
def reset_singleton():
    """Ensure each test starts with a fresh repository."""
    access_request_service.reset_repository_for_tests()
    yield
    access_request_service.reset_repository_for_tests()


class TestRequireFeatureEnabled:
    @patch(
        "api.services.access_request_services"
        ".access_request_service.swagger_settings"
    )
    def test_raises_503_when_disabled(self, mock_settings):
        mock_settings.enable_access_requests = False
        with pytest.raises(HTTPException) as exc:
            access_request_service.require_feature_enabled()
        assert exc.value.status_code == 503

    @patch(
        "api.services.access_request_services"
        ".access_request_service.swagger_settings"
    )
    def test_noop_when_enabled(self, mock_settings):
        mock_settings.enable_access_requests = True
        access_request_service.require_feature_enabled()


class TestCreateAccessRequest:
    @patch(
        "api.services.access_request_services"
        ".access_request_service.swagger_settings"
    )
    @patch(
        "api.services.access_request_services" ".access_request_service.get_repository"
    )
    def test_happy_path(self, mock_get_repo, mock_settings, mock_repo):
        mock_settings.enable_access_requests = True
        mock_repo.find_pending_by_user_sub.return_value = None
        mock_repo.create_pending.return_value = {"_id": "req1", "status": "pending"}
        mock_get_repo.return_value = mock_repo

        user_info = {"sub": "s1", "username": "yutian", "email": "y@x"}
        result = access_request_service.create_access_request(
            user_info, "please let me in"
        )

        assert result["_id"] == "req1"
        mock_repo.create_pending.assert_called_once_with(
            user_sub="s1",
            username="yutian",
            email="y@x",
            justification="please let me in",
        )

    @patch(
        "api.services.access_request_services"
        ".access_request_service.swagger_settings"
    )
    @patch(
        "api.services.access_request_services" ".access_request_service.get_repository"
    )
    def test_duplicate_pending_raises_409(
        self, mock_get_repo, mock_settings, mock_repo
    ):
        mock_settings.enable_access_requests = True
        mock_repo.find_pending_by_user_sub.return_value = {"_id": "old"}
        mock_get_repo.return_value = mock_repo

        with pytest.raises(HTTPException) as exc:
            access_request_service.create_access_request(
                {"sub": "s1", "username": "yutian"}, None
            )
        assert exc.value.status_code == 409

    @patch(
        "api.services.access_request_services"
        ".access_request_service.swagger_settings"
    )
    def test_missing_sub_raises_400(self, mock_settings):
        mock_settings.enable_access_requests = True

        with pytest.raises(HTTPException) as exc:
            access_request_service.create_access_request({"username": "yutian"}, None)
        assert exc.value.status_code == 400

    @patch(
        "api.services.access_request_services"
        ".access_request_service.swagger_settings"
    )
    def test_disabled_raises_503(self, mock_settings):
        mock_settings.enable_access_requests = False

        with pytest.raises(HTTPException) as exc:
            access_request_service.create_access_request(
                {"sub": "s", "username": "u"}, None
            )
        assert exc.value.status_code == 503


class TestListAccessRequests:
    @patch(
        "api.services.access_request_services"
        ".access_request_service.swagger_settings"
    )
    @patch(
        "api.services.access_request_services" ".access_request_service.get_repository"
    )
    def test_default_returns_pending_only(
        self, mock_get_repo, mock_settings, mock_repo
    ):
        mock_settings.enable_access_requests = True
        mock_repo.list.return_value = [{"_id": "r1"}]
        mock_get_repo.return_value = mock_repo

        access_request_service.list_access_requests(None)
        mock_repo.list.assert_called_once_with(status="pending")

    @patch(
        "api.services.access_request_services"
        ".access_request_service.swagger_settings"
    )
    @patch(
        "api.services.access_request_services" ".access_request_service.get_repository"
    )
    def test_all_passes_none_to_repo(self, mock_get_repo, mock_settings, mock_repo):
        mock_settings.enable_access_requests = True
        mock_repo.list.return_value = []
        mock_get_repo.return_value = mock_repo

        access_request_service.list_access_requests("all")
        mock_repo.list.assert_called_once_with(status=None)

    @patch(
        "api.services.access_request_services"
        ".access_request_service.swagger_settings"
    )
    @patch(
        "api.services.access_request_services" ".access_request_service.get_repository"
    )
    def test_specific_status_forwarded(self, mock_get_repo, mock_settings, mock_repo):
        mock_settings.enable_access_requests = True
        mock_repo.list.return_value = []
        mock_get_repo.return_value = mock_repo

        access_request_service.list_access_requests("approved")
        mock_repo.list.assert_called_once_with(status="approved")


class TestApproveAccessRequest:
    @patch(
        "api.services.access_request_services"
        ".access_request_service.swagger_settings"
    )
    @patch(
        "api.services.access_request_services"
        ".access_request_service.affinities_settings"
    )
    @patch("api.services.access_request_services.access_request_service.aai_client")
    @patch(
        "api.services.access_request_services" ".access_request_service.get_repository"
    )
    def test_member_grant_calls_aai_and_marks_approved(
        self,
        mock_get_repo,
        mock_aai,
        mock_affinities,
        mock_settings,
        mock_repo,
    ):
        mock_settings.enable_access_requests = True
        mock_affinities.ep_uuid = "ep-uuid"
        mock_repo.find_by_id.return_value = {
            "_id": "req1",
            "status": "pending",
            "username": "yutian",
        }
        mock_repo.mark_decided.return_value = {"_id": "req1", "status": "approved"}
        mock_get_repo.return_value = mock_repo

        result = access_request_service.approve_access_request(
            request_id="req1",
            admin_info={"sub": "admin-sub", "username": "raul"},
            admin_token="tok",
            grant_type="member",
            notes="welcome",
        )

        mock_aai.add_user_to_group.assert_called_once_with("tok", "ep-uuid", "yutian")
        mock_aai.assign_role.assert_not_called()
        assert result == {"_id": "req1", "status": "approved"}

    @patch(
        "api.services.access_request_services"
        ".access_request_service.swagger_settings"
    )
    @patch(
        "api.services.access_request_services"
        ".access_request_service.affinities_settings"
    )
    @patch("api.services.access_request_services.access_request_service.aai_client")
    @patch(
        "api.services.access_request_services"
        ".access_request_service.endpoint_admin_role_name"
    )
    @patch(
        "api.services.access_request_services" ".access_request_service.get_repository"
    )
    def test_admin_grant_calls_add_user_and_assign_role(
        self,
        mock_get_repo,
        mock_admin_role,
        mock_aai,
        mock_affinities,
        mock_settings,
        mock_repo,
    ):
        mock_settings.enable_access_requests = True
        mock_affinities.ep_uuid = "ep-uuid"
        mock_admin_role.return_value = "ep-uuid_admin"
        mock_repo.find_by_id.return_value = {
            "_id": "req1",
            "status": "pending",
            "username": "yutian",
        }
        mock_repo.mark_decided.return_value = {"_id": "req1"}
        mock_get_repo.return_value = mock_repo

        access_request_service.approve_access_request(
            request_id="req1",
            admin_info={"sub": "as", "username": "raul"},
            admin_token="tok",
            grant_type="admin",
            notes=None,
        )

        mock_aai.add_user_to_group.assert_called_once_with("tok", "ep-uuid", "yutian")
        mock_aai.assign_role.assert_called_once_with("tok", "ep-uuid_admin", "yutian")

    @patch(
        "api.services.access_request_services"
        ".access_request_service.swagger_settings"
    )
    @patch(
        "api.services.access_request_services" ".access_request_service.get_repository"
    )
    def test_unknown_request_raises_404(self, mock_get_repo, mock_settings, mock_repo):
        mock_settings.enable_access_requests = True
        mock_repo.find_by_id.return_value = None
        mock_get_repo.return_value = mock_repo

        with pytest.raises(HTTPException) as exc:
            access_request_service.approve_access_request(
                "req1", {"sub": "as", "username": "r"}, "tok", "member", None
            )
        assert exc.value.status_code == 404

    @patch(
        "api.services.access_request_services"
        ".access_request_service.swagger_settings"
    )
    @patch(
        "api.services.access_request_services" ".access_request_service.get_repository"
    )
    def test_already_decided_raises_409(self, mock_get_repo, mock_settings, mock_repo):
        mock_settings.enable_access_requests = True
        mock_repo.find_by_id.return_value = {"_id": "r1", "status": "approved"}
        mock_get_repo.return_value = mock_repo

        with pytest.raises(HTTPException) as exc:
            access_request_service.approve_access_request(
                "r1", {"sub": "as", "username": "r"}, "tok", "member", None
            )
        assert exc.value.status_code == 409

    @patch(
        "api.services.access_request_services"
        ".access_request_service.swagger_settings"
    )
    @patch(
        "api.services.access_request_services"
        ".access_request_service.affinities_settings"
    )
    @patch("api.services.access_request_services.access_request_service.aai_client")
    @patch(
        "api.services.access_request_services" ".access_request_service.get_repository"
    )
    def test_aai_failure_does_not_mark_approved(
        self,
        mock_get_repo,
        mock_aai,
        mock_affinities,
        mock_settings,
        mock_repo,
    ):
        mock_settings.enable_access_requests = True
        mock_affinities.ep_uuid = "ep-uuid"
        mock_repo.find_by_id.return_value = {
            "_id": "r1",
            "status": "pending",
            "username": "u",
        }
        mock_aai.add_user_to_group.side_effect = HTTPException(
            status_code=403, detail="nope"
        )
        mock_get_repo.return_value = mock_repo

        with pytest.raises(HTTPException) as exc:
            access_request_service.approve_access_request(
                "r1", {"sub": "as", "username": "r"}, "tok", "member", None
            )
        assert exc.value.status_code == 403
        mock_repo.mark_decided.assert_not_called()

    @patch(
        "api.services.access_request_services"
        ".access_request_service.swagger_settings"
    )
    @patch(
        "api.services.access_request_services"
        ".access_request_service.affinities_settings"
    )
    def test_missing_ep_uuid_raises_503(self, mock_affinities, mock_settings):
        mock_settings.enable_access_requests = True
        mock_affinities.ep_uuid = ""

        with patch(
            "api.services.access_request_services"
            ".access_request_service.get_repository"
        ) as mock_get_repo:
            mock_repo = MagicMock()
            mock_repo.find_by_id.return_value = {
                "_id": "r1",
                "status": "pending",
                "username": "u",
            }
            mock_get_repo.return_value = mock_repo

            with pytest.raises(HTTPException) as exc:
                access_request_service.approve_access_request(
                    "r1", {"sub": "as", "username": "r"}, "tok", "member", None
                )
            assert exc.value.status_code == 503


class TestRejectAccessRequest:
    @patch(
        "api.services.access_request_services"
        ".access_request_service.swagger_settings"
    )
    @patch(
        "api.services.access_request_services" ".access_request_service.get_repository"
    )
    def test_happy_path(self, mock_get_repo, mock_settings, mock_repo):
        mock_settings.enable_access_requests = True
        mock_repo.find_by_id.return_value = {
            "_id": "r1",
            "status": "pending",
            "username": "u",
        }
        mock_repo.mark_decided.return_value = {"_id": "r1", "status": "rejected"}
        mock_get_repo.return_value = mock_repo

        result = access_request_service.reject_access_request(
            "r1", {"sub": "as", "username": "r"}, "no thanks"
        )
        assert result["status"] == "rejected"
        mock_repo.mark_decided.assert_called_once_with(
            request_id="r1",
            status="rejected",
            decided_by_sub="as",
            decided_by_username="r",
            grant_type=None,
            decision_notes="no thanks",
        )

    @patch(
        "api.services.access_request_services"
        ".access_request_service.swagger_settings"
    )
    @patch(
        "api.services.access_request_services" ".access_request_service.get_repository"
    )
    def test_unknown_request_raises_404(self, mock_get_repo, mock_settings, mock_repo):
        mock_settings.enable_access_requests = True
        mock_repo.find_by_id.return_value = None
        mock_get_repo.return_value = mock_repo

        with pytest.raises(HTTPException) as exc:
            access_request_service.reject_access_request(
                "r1", {"sub": "as", "username": "r"}, None
            )
        assert exc.value.status_code == 404
