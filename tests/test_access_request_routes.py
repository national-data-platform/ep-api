# tests/test_access_request_routes.py
"""
Tests for the /user/access-requests REST endpoints.
"""

from datetime import datetime, timezone
from unittest.mock import patch

from fastapi import HTTPException
from fastapi.testclient import TestClient

from api.main import app
from api.services.auth_services import get_current_user, require_admin

client = TestClient(app)


def _sample_doc(status_="pending", request_id="r1"):
    return {
        "_id": request_id,
        "user_sub": "sub-yutian",
        "username": "yutian",
        "email": "y@example.com",
        "status": status_,
        "justification": "please",
        "created_at": datetime(2026, 1, 1, tzinfo=timezone.utc),
        "decided_at": None,
        "decided_by_sub": None,
        "decided_by_username": None,
        "grant_type": None,
        "decision_notes": None,
    }


class TestCreateAccessRequest:
    def setup_method(self):
        app.dependency_overrides[get_current_user] = lambda: {
            "sub": "sub-yutian",
            "username": "yutian",
            "email": "y@example.com",
            "roles": ["default-roles-ndp"],
        }

    def teardown_method(self):
        app.dependency_overrides.clear()

    @patch("api.routes.user_routes.access_requests.require_feature_enabled")
    @patch("api.routes.user_routes.access_requests.create_access_request")
    def test_201_returns_request(self, mock_create, mock_flag):
        mock_create.return_value = _sample_doc()

        response = client.post(
            "/user/access-requests",
            json={"justification": "please"},
            headers={"Authorization": "Bearer tok"},
        )
        assert response.status_code == 201
        assert response.json()["id"] == "r1"
        assert response.json()["username"] == "yutian"

    @patch("api.routes.user_routes.access_requests.require_feature_enabled")
    @patch("api.routes.user_routes.access_requests.create_access_request")
    def test_duplicate_surfaces_409(self, mock_create, mock_flag):
        mock_create.side_effect = HTTPException(
            status_code=409, detail="already pending"
        )

        response = client.post(
            "/user/access-requests",
            json={},
            headers={"Authorization": "Bearer tok"},
        )
        assert response.status_code == 409

    def test_rejects_oversized_justification(self):
        response = client.post(
            "/user/access-requests",
            json={"justification": "x" * 2001},
            headers={"Authorization": "Bearer tok"},
        )
        assert response.status_code == 422


class TestListAccessRequests:
    def setup_method(self):
        app.dependency_overrides[require_admin] = lambda: {
            "sub": "admin-sub",
            "username": "raul",
            "roles": ["ndp_admin"],
        }

    def teardown_method(self):
        app.dependency_overrides.clear()

    @patch("api.routes.user_routes.access_requests.require_feature_enabled")
    @patch("api.routes.user_routes.access_requests.list_access_requests")
    def test_list_happy_path(self, mock_list, mock_flag):
        mock_list.return_value = [_sample_doc()]

        response = client.get(
            "/user/access-requests",
            headers={"Authorization": "Bearer tok"},
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["username"] == "yutian"

    def test_invalid_status_returns_422(self):
        response = client.get(
            "/user/access-requests?status=weird",
            headers={"Authorization": "Bearer tok"},
        )
        assert response.status_code == 422

    def test_non_admin_gets_403(self):
        # Simulate require_admin raising a 403 like real life
        def deny():
            raise HTTPException(status_code=403, detail="Administrator role required.")

        app.dependency_overrides[require_admin] = deny

        response = client.get(
            "/user/access-requests",
            headers={"Authorization": "Bearer tok"},
        )
        assert response.status_code == 403


class TestApproveAccessRequest:
    def setup_method(self):
        app.dependency_overrides[require_admin] = lambda: {
            "sub": "admin-sub",
            "username": "raul",
            "roles": ["ndp_admin"],
        }

    def teardown_method(self):
        app.dependency_overrides.clear()

    @patch("api.routes.user_routes.access_requests.require_feature_enabled")
    @patch("api.routes.user_routes.access_requests.approve_access_request")
    def test_approve_member(self, mock_approve, mock_flag):
        approved = _sample_doc(status_="approved")
        approved["grant_type"] = "member"
        approved["decided_by_username"] = "raul"
        mock_approve.return_value = approved

        response = client.post(
            "/user/access-requests/r1/approve",
            json={"grant_type": "member", "notes": "welcome"},
            headers={"Authorization": "Bearer tok"},
        )
        assert response.status_code == 200
        body = response.json()
        assert body["status"] == "approved"
        assert body["grant_type"] == "member"

        # Verify admin token forwarded to service
        call_kwargs = mock_approve.call_args.kwargs
        assert call_kwargs["admin_token"] == "tok"
        assert call_kwargs["grant_type"] == "member"
        assert call_kwargs["notes"] == "welcome"

    def test_invalid_grant_type_returns_422(self):
        response = client.post(
            "/user/access-requests/r1/approve",
            json={"grant_type": "root"},
            headers={"Authorization": "Bearer tok"},
        )
        assert response.status_code == 422

    def test_missing_authorization_returns_401(self):
        # The project's exception handler translates missing bearer to 401
        response = client.post(
            "/user/access-requests/r1/approve",
            json={"grant_type": "member"},
        )
        assert response.status_code == 401


class TestRejectAccessRequest:
    def setup_method(self):
        app.dependency_overrides[require_admin] = lambda: {
            "sub": "admin-sub",
            "username": "raul",
            "roles": ["ndp_admin"],
        }

    def teardown_method(self):
        app.dependency_overrides.clear()

    @patch("api.routes.user_routes.access_requests.require_feature_enabled")
    @patch("api.routes.user_routes.access_requests.reject_access_request")
    def test_reject(self, mock_reject, mock_flag):
        rejected = _sample_doc(status_="rejected")
        rejected["decision_notes"] = "no thanks"
        mock_reject.return_value = rejected

        response = client.post(
            "/user/access-requests/r1/reject",
            json={"notes": "no thanks"},
            headers={"Authorization": "Bearer tok"},
        )
        assert response.status_code == 200
        assert response.json()["status"] == "rejected"
