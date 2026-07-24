import importlib
from types import SimpleNamespace


def test_configured_test_token_bypasses_idp_with_ndp_admin(monkeypatch):
    """The local TEST_TOKEN must enter the normal admin authorization path."""
    module = importlib.import_module("api.services.auth_services.get_current_user")
    monkeypatch.setattr(
        module, "swagger_settings", SimpleNamespace(test_token="local-token")
    )

    user = module.get_current_user(SimpleNamespace(credentials="local-token"))

    assert user["sub"] == "test_user"
    assert user["username"] == "Test User"
    assert user["roles"] == ["ndp_admin"]
    assert user["groups"] == []
