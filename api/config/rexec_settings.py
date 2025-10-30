"""Configuration for Rexec server provisioning."""

from pydantic_settings import BaseSettings


class RexecSettings(BaseSettings):
    """Settings that control the Rexec deployment integration."""

    kubeconfig_local_path: str | None = None
    kubeconfig_mount_path: str | None = "/code/env_variables/.kubeconfig"
    namespace_prefix: str = "rexec-server-"
    namespace_wait_timeout_seconds: int = 60
    broker_service_name: str = "rexec-broker-internal-ip"
    broker_namespace: str = "rexec-broker"
    broker_port: int = 5560
    container_name: str = "rexec-server"
    deployment_manifest_name: str = "rexec-server-deployment.yaml"

    model_config = {
        "env_file": ".env",
        "env_prefix": "REXEC_",
        "extra": "allow"
    }


rexec_settings = RexecSettings()
