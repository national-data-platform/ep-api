#!/usr/bin/env bash
# ==============================================================
# Disposable sandbox for exercising the installer
# ==============================================================
# Runs install.sh inside a throwaway Docker-in-Docker container, so each run
# starts from a clean machine and nothing touches the host's Docker state.
#
#   ./install/tests/sandbox.sh                      # default smoke run
#   ./install/tests/sandbox.sh -- --dry-run --config-id <id>
#   ./install/tests/sandbox.sh --keep -- --backend mongodb
#   ./install/tests/sandbox.sh --shell              # poke around inside
#
# --keep leaves the container running so a failed run can be inspected:
#   docker exec -it ep-installer-sandbox sh
# ==============================================================

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
CONTAINER="ep-installer-sandbox"
IMAGE="docker:28-dind"

keep="false"
want_shell="false"
installer_args=()

while [[ $# -gt 0 ]]; do
  case "$1" in
    --keep)  keep="true"; shift ;;
    --shell) want_shell="true"; shift ;;
    --)      shift; installer_args=("$@"); break ;;
    -h|--help) sed -n '2,18p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
    *)       echo "Unknown option: $1 (use -- to pass arguments to the installer)" >&2; exit 1 ;;
  esac
done

# A run with no installer arguments checks the paths that need no external
# services: render the configuration and stop before starting anything.
[[ ${#installer_args[@]} -gt 0 ]] || installer_args=(--backend mongodb --dry-run --yes)

cleanup() {
  if [[ "$keep" == "true" ]]; then
    echo
    echo "Sandbox left running as '$CONTAINER'. Inspect it with:"
    echo "    docker exec -it $CONTAINER sh"
    echo "    docker rm -f $CONTAINER    # when finished"
  else
    docker rm -f "$CONTAINER" >/dev/null 2>&1 || true
  fi
}
trap cleanup EXIT

docker rm -f "$CONTAINER" >/dev/null 2>&1 || true

echo "==> Starting a clean sandbox ($IMAGE)"
docker run -d --privileged --name "$CONTAINER" \
  -e DOCKER_TLS_CERTDIR="" \
  -e DOCKER_HOST="unix:///var/run/docker.sock" \
  "$IMAGE" >/dev/null

echo "==> Waiting for its Docker daemon"
for attempt in $(seq 1 40); do
  if docker exec "$CONTAINER" docker info >/dev/null 2>&1; then
    echo "    ready"
    break
  fi
  [[ $attempt -eq 40 ]] && { docker logs --tail 20 "$CONTAINER"; echo "Daemon never came up" >&2; exit 1; }
  sleep 1
done

echo "==> Installing what a bare host would need"
docker exec "$CONTAINER" apk add --no-cache bash curl python3 git iproute2 docker-cli-compose >/dev/null 2>&1 \
  || { echo "Could not install sandbox prerequisites" >&2; exit 1; }

echo "==> Copying the working tree in"
# The working tree, not a git export: the point is to test the installer as it
# is right now, including uncommitted changes.
tar -C "$REPO_ROOT" \
    --exclude='.git' --exclude='node_modules' --exclude='.venv' \
    --exclude='ui/build' --exclude='ui/node_modules' --exclude='.env' \
    -cf - . | docker exec -i "$CONTAINER" sh -c 'mkdir -p /opt/ep-api && tar -C /opt/ep-api -xf -'

if [[ "$want_shell" == "true" ]]; then
  echo "==> Dropping into the sandbox (repo at /opt/ep-api)"
  keep="true"
  exec docker exec -it "$CONTAINER" sh -c 'cd /opt/ep-api && exec sh'
fi

echo "==> Running: install.sh ${installer_args[*]}"
echo "---------------------------------------------------------------"

# Give the installer a terminal when the caller has one and has not asked for
# an unattended run, otherwise its prompts can never be exercised here — which
# would leave the interactive path testable only against a real machine.
exec_flags=(-i)
if [[ -t 0 ]] && [[ ! " ${installer_args[*]} " =~ " --yes " ]]; then
  exec_flags+=(-t)
fi

set +e
docker exec "${exec_flags[@]}" "$CONTAINER" bash /opt/ep-api/install/install.sh "${installer_args[@]}"
status=$?
set -e
echo "---------------------------------------------------------------"

if [[ $status -eq 0 ]]; then
  echo "==> Installer finished successfully"
else
  echo "==> Installer exited with status $status" >&2
fi

exit $status
