"""
Utilities for provisioning a user-scoped Rexec server on Kubernetes.
"""

from __future__ import annotations

import hashlib
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Sequence

import yaml
from kubernetes import client, config
from kubernetes.client import ApiClient
from kubernetes.client import exceptions as k8s_exceptions
from packaging.requirements import InvalidRequirement, Requirement
from packaging.specifiers import Specifier

from api.config.rexec_settings import RexecSettings, rexec_settings


class RexecConfigurationError(Exception):
    """Raised when the Rexec deployment configuration is invalid."""


class RexecValidationError(ValueError):
    """Raised when the request payload is invalid."""


class RexecDeploymentError(RuntimeError):
    """Raised when Kubernetes operations fail."""


@dataclass
class KubernetesClients:
    """Typed container for the Kubernetes API clients we interact with."""

    api_client: ApiClient
    core_v1: client.CoreV1Api
    apps_v1: client.AppsV1Api
    networking_v1: client.NetworkingV1Api
    rbac_v1: client.RbacAuthorizationV1Api


def _resolve_kubeconfig_path(settings: RexecSettings) -> str:
    """
    Resolve the kubeconfig path, preferring the mounted path inside the container
    and falling back to a host-local path for non-container execution.
    """
    candidates: List[str] = []

    if settings.kubeconfig_mount_path:
        candidates.append(settings.kubeconfig_mount_path)
        print(f"kubeconfig mount path: {settings.kubeconfig_mount_path}")

    if settings.kubeconfig_local_path:
        candidates.append(settings.kubeconfig_local_path)
        print(f"kubeconfig local path: {settings.kubeconfig_local_path}")

    for candidate in candidates:
        candidate_path = Path(candidate).expanduser()
        if candidate_path.exists():
            print(f"Using kubeconfig path: {candidate_path}")
            return str(candidate_path)

    raise RexecConfigurationError(
        "Kubeconfig file not found. Set 'REXEC_KUBECONFIG_MOUNT_PATH' for the "
        "in-container path or 'REXEC_KUBECONFIG_LOCAL_PATH' for the host path."
    )


def _load_kubernetes_clients(kubeconfig_path: str) -> KubernetesClients:
    """Load Kubernetes configuration and initialize client instances."""
    try:
        config.load_kube_config(config_file=kubeconfig_path)
    except Exception as exc:  # noqa: BLE001 - preserve original error context
        raise RexecConfigurationError(
            f"Failed to load kubeconfig from '{kubeconfig_path}': {exc}"
        ) from exc

    api_client = client.ApiClient()
    return KubernetesClients(
        api_client=api_client,
        core_v1=client.CoreV1Api(api_client),
        apps_v1=client.AppsV1Api(api_client),
        networking_v1=client.NetworkingV1Api(api_client),
        rbac_v1=client.RbacAuthorizationV1Api(api_client),
    )


def _load_yaml_documents(file_path: Path) -> List[dict]:
    """Load one or more YAML documents from a path."""
    if not file_path.exists():
        raise RexecConfigurationError(f"Manifest file not found: {file_path}")

    with file_path.open("r", encoding="utf-8") as handle:
        return [doc for doc in yaml.safe_load_all(handle) if doc]


def _namespace_exists(clients: KubernetesClients, namespace: str) -> bool:
    """Check whether the requested namespace already exists."""
    try:
        clients.core_v1.read_namespace(name=namespace)
        return True
    except k8s_exceptions.ApiException as exc:
        if exc.status == 404:
            return False
        raise RexecDeploymentError(
            f"Failed to read namespace '{namespace}': {exc}"
        ) from exc


def _wait_for_namespace(
    clients: KubernetesClients,
    namespace: str,
    timeout_seconds: int,
) -> None:
    """Poll until the namespace is available or the timeout expires."""
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        if _namespace_exists(clients, namespace):
            return
        time.sleep(1)
    raise RexecDeploymentError(
        f"Timeout waiting for namespace '{namespace}' to be created"
    )


def _apply_manifest(
    clients: KubernetesClients,
    manifest: dict,
    namespace: str,
) -> None:
    """
    Apply a namespace-scoped manifest, handling AlreadyExists conflicts gracefully.
    """
    kind = manifest.get("kind")
    metadata = manifest.get("metadata", {})
    name = metadata.get("name", "<unknown>")

    try:
        if kind == "Namespace":
            clients.core_v1.create_namespace(body=manifest)
        elif kind == "Deployment":
            clients.apps_v1.create_namespaced_deployment(
                namespace=namespace,
                body=manifest,
            )
        elif kind == "Service":
            clients.core_v1.create_namespaced_service(
                namespace=namespace,
                body=manifest,
            )
        elif kind == "ConfigMap":
            clients.core_v1.create_namespaced_config_map(
                namespace=namespace,
                body=manifest,
            )
        elif kind == "Role":
            clients.rbac_v1.create_namespaced_role(
                namespace=namespace,
                body=manifest,
            )
        elif kind == "RoleBinding":
            clients.rbac_v1.create_namespaced_role_binding(
                namespace=namespace,
                body=manifest,
            )
        elif kind == "Ingress":
            clients.networking_v1.create_namespaced_ingress(
                namespace=namespace,
                body=manifest,
            )
        elif kind == "NetworkPolicy":
            clients.networking_v1.create_namespaced_network_policy(
                namespace=namespace,
                body=manifest,
            )
        else:
            raise RexecDeploymentError(f"Unsupported manifest kind: {kind}")
    except k8s_exceptions.ApiException as exc:
        if exc.status == 409:  # AlreadyExists
            return
        raise RexecDeploymentError(
            f"Failed to apply {kind} '{name}': {exc}"
        ) from exc


def _get_cluster_ip(
    clients: KubernetesClients,
    service_name: str,
    namespace: str,
) -> str:
    """Retrieve the ClusterIP for a named service."""
    try:
        service = clients.core_v1.read_namespaced_service(
            name=service_name,
            namespace=namespace,
        )
    except k8s_exceptions.ApiException as exc:
        raise RexecDeploymentError(
            f"Failed to fetch service '{service_name}' in namespace '{namespace}': {exc}"
        ) from exc

    cluster_ip = service.spec.cluster_ip
    if not cluster_ip:
        raise RexecDeploymentError(
            f"Service '{service_name}' does not expose a ClusterIP"
        )
    return cluster_ip


def _deployment_with_digest_exists(
    clients: KubernetesClients,
    namespace: str,
    digest: str,
) -> bool:
    """Determine if a deployment already exists with the provided digest label."""
    try:
        deployments = clients.apps_v1.list_namespaced_deployment(
            namespace=namespace,
            label_selector=f"digest={digest}",
        )
    except k8s_exceptions.ApiException as exc:
        raise RexecDeploymentError(
            f"Failed to list deployments in namespace '{namespace}': {exc}"
        ) from exc

    return bool(deployments.items)


def _parse_requirements(requirements: Iterable[str]) -> tuple[str, List[str]]:
    """
    Separate the python version requirement from the rest of the packages.
    Returns a tuple of (python_version, user_requirements_list).
    """
    python_version: str | None = None
    user_requirements: List[str] = []

    for raw_requirement in requirements:
        requirement_str = raw_requirement.strip()
        if not requirement_str:
            continue
        try:
            parsed = Requirement(requirement_str)
        except InvalidRequirement as exc:
            raise RexecValidationError(
                f"Invalid requirement '{requirement_str}': {exc}"
            ) from exc

        if parsed.name.lower() == "python":
            try:
                specifier: Specifier = next(iter(parsed.specifier))
            except StopIteration as exc:
                raise RexecValidationError(
                    "Python requirement must pin the version using '=='."
                ) from exc

            if specifier.operator != "==":
                raise RexecValidationError(
                    "Python requirement must use '==' to pin a single version."
                )
            python_version = specifier.version
        else:
            user_requirements.append(requirement_str)

    if not python_version:
        raise RexecValidationError(
            "A pinned Python version (e.g., 'python==3.11') is required."
        )

    return python_version, user_requirements


def _load_builtin_requirements() -> List[str]:
    """Read the packaged requirements for the base Rexec server image."""
    requirements_file = Path(__file__).parent / "SciDx_rexec_server" / "requirements.txt"
    if not requirements_file.exists():
        raise RexecConfigurationError(
            f"Builtin requirements file missing: {requirements_file}"
        )

    requirements: List[str] = []
    with requirements_file.open("r", encoding="utf-8") as handle:
        for line in handle:
            requirement = line.strip()
            if requirement and not requirement.startswith("#"):
                requirements.append(requirement)

    return requirements


def _prepare_deployment_manifest(
    manifest: dict,
    namespace: str,
    digest: str,
    python_version: str,
    builtin_requirements: Sequence[str],
    user_requirements: Sequence[str],
    broker_addr: str,
    settings: RexecSettings,
) -> dict:
    """
    Mutate a deployment manifest in-place with namespace, labels, image, and command.
    """
    manifest.setdefault("metadata", {})
    manifest["metadata"]["namespace"] = namespace

    labels = manifest["metadata"].setdefault("labels", {})
    labels["digest"] = digest

    spec = manifest.setdefault("spec", {})
    template = spec.setdefault("template", {})
    template_metadata = template.setdefault("metadata", {})
    template_metadata.setdefault("labels", {})["digest"] = digest

    pod_spec = template.setdefault("spec", {})
    containers = pod_spec.setdefault("containers", [])

    builtin_requirements_str = " ".join(builtin_requirements)
    user_requirements_str = " ".join(user_requirements)

    for container in containers:
        if container.get("name") != settings.container_name:
            continue

        container["image"] = f"python:{python_version}"

        command = container.get("command")
        if command and isinstance(command, list) and command:
            command[-1] = (
                command[-1]
                .replace("${builtin_requirements}", builtin_requirements_str)
                .replace("${user_requirements}", user_requirements_str)
                .replace("${broker_addr}", broker_addr)
                .replace("${broker_port}", str(settings.broker_port))
            )

    return manifest


def create_rexec_server_resources(
    group_id: str,
    user_id: str,
    requirements: Iterable[str],
    *,
    settings: RexecSettings | None = None,
) -> str:
    """
    Create the Kubernetes resources required for a user's dedicated Rexec server.
    """
    resolved_settings = settings or rexec_settings
    kubeconfig_path = _resolve_kubeconfig_path(resolved_settings)
    clients = _load_kubernetes_clients(kubeconfig_path)

    namespace = f"{resolved_settings.namespace_prefix}{user_id}"

    namespace_exists = _namespace_exists(clients, namespace)
    if not namespace_exists:
        namespace_manifest = {
            "apiVersion": "v1",
            "kind": "Namespace",
            "metadata": {"name": namespace},
        }
        _apply_manifest(clients, namespace_manifest, namespace=namespace)
        _wait_for_namespace(
            clients,
            namespace,
            resolved_settings.namespace_wait_timeout_seconds,
        )

    python_version, user_requirements = _parse_requirements(requirements)

    digest_components = sorted(user_requirements)
    digest_components.insert(0, f"python=={python_version}")
    digest = hashlib.sha1(" ".join(digest_components).encode("utf-8")).hexdigest()

    if namespace_exists and _deployment_with_digest_exists(clients, namespace, digest):
        return "remote execution server instance with user-provided requirements exists."

    builtin_requirements = _load_builtin_requirements()

    manifest_dir = Path(__file__).parent / "k8s"
    deployment_manifests = _load_yaml_documents(
        manifest_dir / resolved_settings.deployment_manifest_name
    )

    broker_addr = _get_cluster_ip(
        clients,
        resolved_settings.broker_service_name,
        resolved_settings.broker_namespace,
    )

    for manifest in deployment_manifests:
        if manifest.get("kind") == "Deployment":
            manifest = _prepare_deployment_manifest(
                manifest,
                namespace,
                digest,
                python_version,
                builtin_requirements,
                user_requirements,
                broker_addr,
                resolved_settings,
            )
        else:
            manifest.setdefault("metadata", {})["namespace"] = namespace

        _apply_manifest(clients, manifest, namespace=namespace)

    return "remote execution server instance created for user."
