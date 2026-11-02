"""
The test token is off unless explicitly configured (issue #383).

``test_token`` used to default to ``testing_token``, a value published in this
repository, and ``example.env`` (which the installer renders ``.env`` from)
set the same value. Every installer-made Endpoint therefore accepted
``Bearer testing_token`` as a platform administrator.
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException, status

from api.config.swagger_settings import Settings
from api.services.auth_services.get_current_user import get_current_user

REPO = Path(__file__).resolve().parents[1]


class _Creds:
    def __init__(self, token):
        self.credentials = token


def _rejected_by_auth_service():
    r = MagicMock()
    r.status_code = 401
    return r


def test_code_default_is_empty(monkeypatch):
    monkeypatch.delenv("TEST_TOKEN", raising=False)
    assert Settings(_env_file=None).test_token == ""


def test_example_env_leaves_it_empty():
    lines = (REPO / "example.env").read_text().splitlines()
    assert "TEST_TOKEN=" in lines
    assert not any(
        line.startswith("TEST_TOKEN=") and line != "TEST_TOKEN=" for line in lines
    )


@pytest.mark.parametrize("token", ["testing_token", ""])
def test_with_an_empty_test_token_nothing_bypasses_the_auth_service(token):
    with (
        patch(
            "api.services.auth_services.get_current_user.swagger_settings"
        ) as settings,
        patch(
            "api.services.auth_services.get_current_user.requests.post",
            return_value=_rejected_by_auth_service(),
        ) as post,
    ):
        settings.test_token = ""
        settings.auth_api_url = "https://aai.example.org/information"
        with pytest.raises(HTTPException) as exc:
            get_current_user(token_data=_Creds(token))

    assert exc.value.status_code == status.HTTP_401_UNAUTHORIZED
    post.assert_called_once()


def test_a_configured_test_token_still_works():
    with patch(
        "api.services.auth_services.get_current_user.swagger_settings"
    ) as settings:
        settings.test_token = "dev-only-token"
        user = get_current_user(token_data=_Creds("dev-only-token"))

    assert user["roles"] == ["ndp_admin"]
