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
    @patch("api.services.access_request_services.access_request_service.aai_client")
    @patch(
        "api.services.access_request_services" ".access_request_service.get_repository"
    )
    def test_member_grant_calls_aai_and_marks_approved(
        self,
        mock_get_repo,
        mock_aai,
        mock_settings,
        mock_repo,
    ):
        mock_settings.enable_access_requests = True
        mock_settings.oidc_service_client_id = "ep-123"
        mock_repo.find_by_id.return_value = {
            "_id": "req1",
            "status": "pending",
            "username": "yutian",
            "user_sub": "yutian-uuid",
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

        mock_aai.add_user_to_group.assert_called_once_with(
            "tok",
            "ndp_ep/ep-123",
            "yutian-uuid",
            "viewer",
            client_assertion=mock_aai.client_login.return_value,
        )
        assert result == {"_id": "req1", "status": "approved"}

    @patch(
        "api.services.access_request_services"
        ".access_request_service.swagger_settings"
    )
    @patch("api.services.access_request_services.access_request_service.aai_client")
    @patch(
        "api.services.access_request_services" ".access_request_service.get_repository"
    )
    def test_admin_grant_adds_to_group_as_admin(
        self,
        mock_get_repo,
        mock_aai,
        mock_settings,
        mock_repo,
    ):
        """admin grant joins the group at its admin level, which passes the
        admin-area gate."""
        mock_settings.enable_access_requests = True
        mock_settings.oidc_service_client_id = "ep-123"
        mock_repo.find_by_id.return_value = {
            "_id": "req1",
            "status": "pending",
            "username": "yutian",
            "user_sub": "yutian-uuid",
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

        mock_aai.add_user_to_group.assert_called_once_with(
            "tok",
            "ndp_ep/ep-123",
            "yutian-uuid",
            "admin",
            client_assertion=mock_aai.client_login.return_value,
        )

    @patch(
        "api.services.access_request_services"
        ".access_request_service.swagger_settings"
    )
    @patch("api.services.access_request_services.access_request_service.aai_client")
    @patch(
        "api.services.access_request_services" ".access_request_service.get_repository"
    )
    def test_viewer_grant_only_adds_to_group(
        self,
        mock_get_repo,
        mock_aai,
        mock_settings,
        mock_repo,
    ):
        """viewer grant joins the group at its viewer level, the AAI's
        default, which passes viewer-area only."""
        mock_settings.enable_access_requests = True
        mock_settings.oidc_service_client_id = "ep-123"
        mock_repo.find_by_id.return_value = {
            "_id": "req1",
            "status": "pending",
            "username": "yutian",
            "user_sub": "yutian-uuid",
        }
        mock_repo.mark_decided.return_value = {"_id": "req1", "status": "approved"}
        mock_get_repo.return_value = mock_repo

        access_request_service.approve_access_request(
            request_id="req1",
            admin_info={"sub": "as", "username": "raul"},
            admin_token="tok",
            grant_type="viewer",
            notes=None,
        )

        mock_aai.add_user_to_group.assert_called_once_with(
            "tok",
            "ndp_ep/ep-123",
            "yutian-uuid",
            "viewer",
            client_assertion=mock_aai.client_login.return_value,
        )

    @patch(
        "api.services.access_request_services"
        ".access_request_service.swagger_settings"
    )
    @patch("api.services.access_request_services.access_request_service.aai_client")
    @patch(
        "api.services.access_request_services" ".access_request_service.get_repository"
    )
    def test_writer_grant_adds_to_group_as_editor(
        self,
        mock_get_repo,
        mock_aai,
        mock_settings,
        mock_repo,
    ):
        """writer grant joins the group at its editor level: the identity
        provider's name for the write tier, which passes editor-area."""
        mock_settings.enable_access_requests = True
        mock_settings.oidc_service_client_id = "ep-123"
        mock_repo.find_by_id.return_value = {
            "_id": "req1",
            "status": "pending",
            "username": "yutian",
            "user_sub": "yutian-uuid",
        }
        mock_repo.mark_decided.return_value = {"_id": "req1"}
        mock_get_repo.return_value = mock_repo

        access_request_service.approve_access_request(
            request_id="req1",
            admin_info={"sub": "as", "username": "raul"},
            admin_token="tok",
            grant_type="writer",
            notes=None,
        )

        mock_aai.add_user_to_group.assert_called_once_with(
            "tok",
            "ndp_ep/ep-123",
            "yutian-uuid",
            "editor",
            client_assertion=mock_aai.client_login.return_value,
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
    @patch("api.services.access_request_services.access_request_service.aai_client")
    @patch(
        "api.services.access_request_services" ".access_request_service.get_repository"
    )
    def test_aai_failure_does_not_mark_approved(
        self,
        mock_get_repo,
        mock_aai,
        mock_settings,
        mock_repo,
    ):
        mock_settings.enable_access_requests = True
        mock_settings.oidc_service_client_id = "ep-123"
        mock_repo.find_by_id.return_value = {
            "_id": "r1",
            "status": "pending",
            "username": "u",
            "user_sub": "u-uuid",
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
    def test_without_a_client_approval_raises_503(self, mock_settings):
        mock_settings.enable_access_requests = True
        mock_settings.oidc_service_client_id = ""

        with patch(
            "api.services.access_request_services"
            ".access_request_service.get_repository"
        ) as mock_get_repo:
            mock_repo = MagicMock()
            mock_repo.find_by_id.return_value = {
                "_id": "r1",
                "status": "pending",
                "user_sub": "u-uuid",
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
