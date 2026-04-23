# tests/test_aai_client.py
"""
Tests for the NDP AAI API client wrapper.
"""

from unittest.mock import MagicMock, patch

import pytest
import requests
from fastapi import HTTPException

from api.services.auth_services import aai_client


class TestAaiBaseUrl:
    @patch("api.services.auth_services.aai_client.swagger_settings")
    def test_strips_path_and_keeps_port(self, mock_settings):
        mock_settings.auth_api_url = "http://idp.example.com:5055/information"
        assert aai_client._aai_base_url() == "http://idp.example.com:5055"

    @patch("api.services.auth_services.aai_client.swagger_settings")
    def test_raises_when_url_is_empty(self, mock_settings):
        mock_settings.auth_api_url = ""
        with pytest.raises(HTTPException) as exc:
            aai_client._aai_base_url()
        assert exc.value.status_code == 502


class TestAddUserToGroup:
    @patch("api.services.auth_services.aai_client.requests.post")
    @patch("api.services.auth_services.aai_client.swagger_settings")
    def test_happy_path_forwards_token(self, mock_settings, mock_post):
        mock_settings.auth_api_url = "http://idp.example.com:5055/information"

        resp = MagicMock()
        resp.status_code = 200
        resp.content = b'{"message":"ok"}'
        resp.json.return_value = {"message": "ok"}
        mock_post.return_value = resp

        result = aai_client.add_user_to_group("tok", "some-group", "yutian")

        assert result == {"message": "ok"}
        mock_post.assert_called_once_with(
            "http://idp.example.com:5055/group/add-user",
            headers={"Authorization": "Bearer tok"},
            json={"group_name": "some-group", "username": "yutian"},
            timeout=15,
        )

    @patch("api.services.auth_services.aai_client.requests.post")
    @patch("api.services.auth_services.aai_client.swagger_settings")
    def test_forbidden_response_surfaces_as_403(self, mock_settings, mock_post):
        mock_settings.auth_api_url = "http://idp.example.com:5055/information"

        resp = MagicMock()
        resp.status_code = 403
        resp.content = b'{"detail":"insufficient group privileges"}'
        resp.json.return_value = {"detail": "insufficient group privileges"}
        mock_post.return_value = resp

        with pytest.raises(HTTPException) as exc:
            aai_client.add_user_to_group("tok", "some-group", "yutian")
        assert exc.value.status_code == 403
        assert "insufficient" in exc.value.detail

    @patch("api.services.auth_services.aai_client.requests.post")
    @patch("api.services.auth_services.aai_client.swagger_settings")
    def test_unauthorized_response_surfaces_as_401(self, mock_settings, mock_post):
        mock_settings.auth_api_url = "http://idp.example.com:5055/information"

        resp = MagicMock()
        resp.status_code = 401
        resp.content = b'{"detail":"Missing token"}'
        resp.json.return_value = {"detail": "Missing token"}
        mock_post.return_value = resp

        with pytest.raises(HTTPException) as exc:
            aai_client.add_user_to_group("tok", "some-group", "yutian")
        assert exc.value.status_code == 401

    @patch("api.services.auth_services.aai_client.requests.post")
    @patch("api.services.auth_services.aai_client.swagger_settings")
    def test_not_found_surfaces_as_404(self, mock_settings, mock_post):
        mock_settings.auth_api_url = "http://idp.example.com:5055/information"

        resp = MagicMock()
        resp.status_code = 404
        resp.content = b'{"detail":"user not found"}'
        resp.json.return_value = {"detail": "user not found"}
        mock_post.return_value = resp

        with pytest.raises(HTTPException) as exc:
            aai_client.add_user_to_group("tok", "g", "ghost")
        assert exc.value.status_code == 404

    @patch("api.services.auth_services.aai_client.requests.post")
    @patch("api.services.auth_services.aai_client.swagger_settings")
    def test_unexpected_status_surfaces_as_502(self, mock_settings, mock_post):
        mock_settings.auth_api_url = "http://idp.example.com:5055/information"

        resp = MagicMock()
        resp.status_code = 500
        resp.content = b'{"detail":"boom"}'
        resp.json.return_value = {"detail": "boom"}
        mock_post.return_value = resp

        with pytest.raises(HTTPException) as exc:
            aai_client.add_user_to_group("tok", "g", "u")
        assert exc.value.status_code == 502

    @patch("api.services.auth_services.aai_client.requests.post")
    @patch("api.services.auth_services.aai_client.swagger_settings")
    def test_transport_error_becomes_502(self, mock_settings, mock_post):
        mock_settings.auth_api_url = "http://idp.example.com:5055/information"
        mock_post.side_effect = requests.exceptions.ConnectionError("boom")

        with pytest.raises(HTTPException) as exc:
            aai_client.add_user_to_group("tok", "g", "u")
        assert exc.value.status_code == 502


class TestAssignRole:
    @patch("api.services.auth_services.aai_client.requests.post")
    @patch("api.services.auth_services.aai_client.swagger_settings")
    def test_happy_path(self, mock_settings, mock_post):
        mock_settings.auth_api_url = "http://idp.example.com:5055/information"

        resp = MagicMock()
        resp.status_code = 200
        resp.content = b"{}"
        resp.json.return_value = {}
        mock_post.return_value = resp

        aai_client.assign_role("tok", "my-role", "yutian")

        mock_post.assert_called_once_with(
            "http://idp.example.com:5055/role/assign",
            headers={"Authorization": "Bearer tok"},
            json={"role_name": "my-role", "username": "yutian"},
            timeout=15,
        )


class TestListGroupMembers:
    @patch("api.services.auth_services.aai_client.requests.get")
    @patch("api.services.auth_services.aai_client.swagger_settings")
    def test_happy_path(self, mock_settings, mock_get):
        mock_settings.auth_api_url = "http://idp.example.com:5055/information"

        resp = MagicMock()
        resp.status_code = 200
        resp.json.return_value = {"yutian": ["viewer"]}
        mock_get.return_value = resp

        result = aai_client.list_group_members("tok", "g")

        assert result == {"yutian": ["viewer"]}
        mock_get.assert_called_once_with(
            "http://idp.example.com:5055/group/members",
            headers={"Authorization": "Bearer tok"},
            params={"group_name": "g"},
            timeout=15,
        )

    @patch("api.services.auth_services.aai_client.requests.get")
    @patch("api.services.auth_services.aai_client.swagger_settings")
    def test_empty_group_returns_empty_dict(self, mock_settings, mock_get):
        mock_settings.auth_api_url = "http://idp.example.com:5055/information"

        resp = MagicMock()
        resp.status_code = 200
        resp.json.return_value = {}
        mock_get.return_value = resp

        assert aai_client.list_group_members("tok", "g") == {}
