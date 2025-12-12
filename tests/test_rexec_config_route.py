from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.routes.rexec_routes import router as rexec_router
import api.routes.rexec_routes.get_rexec_config as get_config_module


def _build_app() -> FastAPI:
    app = FastAPI()
    app.include_router(rexec_router)
    return app


def test_get_rexec_config_success(monkeypatch):
    def fake_get_rexec_config(*, api_url: str | None, default_external_host=None):
        return {
            "api_url": api_url,
            "broker_external_host": default_external_host or "1.2.3.4",
            "broker_external_port": 30001,
            "broker_external_url": "1.2.3.4:30001",
        }

    monkeypatch.setattr(
        get_config_module.rexec_services,
        "get_rexec_config",
        fake_get_rexec_config,
    )

    client = TestClient(_build_app())
    response = client.get("/rexec/config")

    assert response.status_code == 200
    data = response.json()
    assert data["api_url"] == "http://testserver/rexec"
    assert data["broker_external_host"]
    assert data["broker_external_port"] == 30001
    assert data["broker_external_url"]


def test_get_rexec_config_failure(monkeypatch):
    def fake_get_rexec_config(*, api_url: str | None, default_external_host=None):
        raise RuntimeError("cannot load broker")

    monkeypatch.setattr(
        get_config_module.rexec_services,
        "get_rexec_config",
        fake_get_rexec_config,
    )

    client = TestClient(_build_app())
    response = client.get("/rexec/config")

    assert response.status_code == 500
    assert "Failed to retrieve Rexec configuration" in response.json()["detail"]
