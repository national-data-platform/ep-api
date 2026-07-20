#!/usr/bin/env bash
# ==============================================================
# NDP Endpoint installer
# ==============================================================
# Materialises a deployment from a Federation registration.
#
# The operator registers the Endpoint with the Federation, receives a
# configuration id, and this script turns it into a running deployment:
#
#   ./install/install.sh --config-id 6a5e300b7770ef7b55e0ce6b
#
# Two rules this installer follows, both learned from the previous one:
#
#   1. It never edits repository files. The previous installer patched
#      docker-compose.yml with a literal sed that stopped matching when the
#      file changed, and failed silently for months. Everything here is done
#      through environment variables and compose profiles.
#
#   2. It never keeps its own list of settings. The .env is rendered from
#      example.env, which is the documented source of truth, so a variable
#      added there appears in new installations automatically.
# ==============================================================

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
FEDERATION_URL_DEFAULT="https://federation.ndp.utah.edu"

config_id=""
federation_url="$FEDERATION_URL_DEFAULT"
backend="mongodb"
ckan_url=""
ckan_api_key=""
ep_api_port="8002"
dry_run="false"
start="true"
assume_yes="false"

RED=$'\033[0;31m'; GREEN=$'\033[0;32m'; YELLOW=$'\033[1;33m'
BLUE=$'\033[0;34m'; NC=$'\033[0m'

info()    { echo "${BLUE}[info]${NC} $*"; }
ok()      { echo "${GREEN}[ ok ]${NC} $*"; }
warn()    { echo "${YELLOW}[warn]${NC} $*" >&2; }
fail()    { echo "${RED}[fail]${NC} $*" >&2; exit 1; }
step()    { echo; echo "${GREEN}==>${NC} $*"; }

usage() {
  cat <<USAGE
NDP Endpoint installer

Usage:
  install.sh --config-id <id> [options]
  install.sh --backend mongodb [options]        # standalone, no Federation

Options:
  --config-id <id>        Federation configuration id for this Endpoint.
  --federation-url <url>  Default: $FEDERATION_URL_DEFAULT
  --backend <name>        Local catalog backend: mongodb | ckan. Default: mongodb
  --ckan-url <url>        Existing CKAN to use when --backend ckan
  --ckan-api-key <key>    API key for that CKAN
  --ep-api-port <port>    Host port to publish the API on. Default: 8002
  --dry-run               Render .env and run the checks, start nothing
  --no-start              Write everything, do not bring the stack up
  --yes                   Do not prompt before overwriting an existing .env
  -h, --help              This message

The configuration id comes from registering the Endpoint with the Federation.
Values it supplies (organization, groups, streaming, staging catalog, identity
provider) are applied on top of the documented defaults in example.env.
USAGE
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --config-id)       config_id="${2:-}"; shift 2 ;;
    --federation-url)  federation_url="${2:-}"; shift 2 ;;
    --backend)         backend="${2:-}"; shift 2 ;;
    --ckan-url)        ckan_url="${2:-}"; shift 2 ;;
    --ckan-api-key)    ckan_api_key="${2:-}"; shift 2 ;;
    --ep-api-port)     ep_api_port="${2:-}"; shift 2 ;;
    --dry-run)         dry_run="true"; shift ;;
    --no-start)        start="false"; shift ;;
    --yes)             assume_yes="true"; shift ;;
    -h|--help)         usage; exit 0 ;;
    *)                 fail "Unknown option: $1 (try --help)" ;;
  esac
done

[[ "$backend" == "mongodb" || "$backend" == "ckan" ]] \
  || fail "--backend must be mongodb or ckan (got: $backend)"

# --------------------------------------------------------------
step "Checking prerequisites"
# --------------------------------------------------------------
for cmd in curl python3 docker; do
  command -v "$cmd" >/dev/null 2>&1 || fail "$cmd is required but not installed."
done

if docker compose version >/dev/null 2>&1; then
  COMPOSE=(docker compose)
elif command -v docker-compose >/dev/null 2>&1; then
  COMPOSE=(docker-compose)
else
  fail "Docker Compose is required (neither 'docker compose' nor 'docker-compose' found)."
fi

docker info >/dev/null 2>&1 || fail "Cannot talk to the Docker daemon. Is it running, and is this user allowed to use it?"
[[ -f "$REPO_ROOT/example.env" ]] || fail "example.env not found at $REPO_ROOT — run this from a checkout of the repository."
ok "curl, python3, docker and compose are available"

# --------------------------------------------------------------
# Collect the values that will override the documented defaults.
# --------------------------------------------------------------
overrides_file="$(mktemp)"
trap 'rm -f "$overrides_file" "${config_file:-}"' EXIT
echo '{}' > "$overrides_file"

put() {
  # put KEY VALUE — records an override, JSON-encoding the value safely.
  python3 - "$overrides_file" "$1" "$2" <<'PY'
import json, sys
path, key, value = sys.argv[1], sys.argv[2], sys.argv[3]
with open(path) as handle:
    data = json.load(handle)
data[key] = value
with open(path, "w") as handle:
    json.dump(data, handle)
PY
}

# example.env is written as a demo that shows every setting, so its defaults
# have the optional integrations switched on. Inheriting those would produce an
# Endpoint pointing at Kafka, MinIO, JupyterLab and Pelican that nothing has
# provisioned. Everything optional starts off here, and is switched back on
# further down only when something actually provides it.
put KAFKA_CONNECTION "False"
put USE_JUPYTERLAB "False"
put S3_ENABLED "False"
put PELICAN_ENABLED "False"
put AFFINITIES_ENABLED "False"
put REXEC_CONNECTION "False"
put PRE_CKAN_ENABLED "False"
put OIDC_ENABLED "False"

if [[ -n "$config_id" ]]; then
  step "Fetching the Federation registration"
  config_file="$(mktemp)"
  http_code="$(curl -s -o "$config_file" -w '%{http_code}' -m 30 \
    "${federation_url%/}/ep/${config_id}" || echo 000)"

  case "$http_code" in
    200) ;;
    404) fail "Configuration $config_id not found at ${federation_url%/}. Check the id and --federation-url." ;;
    000) fail "Could not reach the Federation at ${federation_url%/}." ;;
    *)   fail "Federation returned HTTP $http_code for $config_id." ;;
  esac

  python3 -c "import json,sys; json.load(open(sys.argv[1]))" "$config_file" \
    2>/dev/null || fail "Federation returned a response that is not valid JSON."

  # Translate the registration into Endpoint settings. Anything the
  # registration does not mention keeps its documented default.
  eval "$(python3 - "$config_file" <<'PY'
import json, shlex, sys

cfg = json.load(open(sys.argv[1]))


def truthy(value):
    return str(value).strip().lower() in ("true", "1", "yes", "on")


def emit(name, value):
    print(f"{name}={shlex.quote(str(value))}")


emit("fed_org", cfg.get("organization") or "")
emit("fed_ep_name", cfg.get("ep_name") or "")
emit("fed_group", cfg.get("group_name") or "")
emit("fed_streaming", "true" if truthy(cfg.get("streaming")) else "false")
emit("fed_jhub", "true" if truthy(cfg.get("jhub")) else "false")
emit("fed_jupyter_url", cfg.get("jupyter_url") or "")
emit("fed_pre_ckan_url", cfg.get("pre_ckan_url") or "")
emit("fed_pre_ckan_key", cfg.get("pre_ckan_key") or "")
emit("fed_realm", cfg.get("realm_name") or "NDP")
emit("fed_client_id", cfg.get("client_id") or "")
emit("fed_public", "true" if truthy(cfg.get("public")) else "false")
PY
)"

  ok "Registration for '${fed_ep_name:-unnamed}' (${fed_org:-no organization})"

  [[ -n "$fed_org" ]]      && put ORGANIZATION "$fed_org"
  [[ -n "$fed_ep_name" ]]  && put EP_NAME "$fed_ep_name"

  if [[ -n "$fed_group" ]]; then
    put ENABLE_GROUP_BASED_ACCESS "True"
    put GROUP_NAMES "$fed_group"
  fi

  if [[ "$fed_streaming" == "true" ]]; then
    put KAFKA_CONNECTION "True"
  else
    put KAFKA_CONNECTION "False"
  fi

  if [[ "$fed_jhub" == "true" ]]; then
    put USE_JUPYTERLAB "True"
    [[ -n "$fed_jupyter_url" ]] && put JUPYTER_URL "$fed_jupyter_url"
  else
    put USE_JUPYTERLAB "False"
  fi

  if [[ -n "$fed_pre_ckan_url" && -n "$fed_pre_ckan_key" ]]; then
    put PRE_CKAN_ENABLED "True"
    put PRE_CKAN_URL "$fed_pre_ckan_url"
    put PRE_CKAN_API_KEY "$fed_pre_ckan_key"
  else
    put PRE_CKAN_ENABLED "False"
  fi

  put IS_PUBLIC "$([[ "$fed_public" == "true" ]] && echo True || echo False)"

  # The registration names the realm but not the identity provider host, and
  # the Endpoint must validate tokens against the same provider that issues
  # them. Deriving one from the other is guesswork, so identity-provider
  # sign-in is left switched off for the operator to configure deliberately.
  if [[ -n "$fed_client_id" ]]; then
    info "Registration includes client id '$fed_client_id' for realm '$fed_realm'."
    info "Identity-provider sign-in is left off; see docs/configuration.md to enable it."
  fi
else
  warn "No --config-id given: installing without a Federation registration."
  warn "The Endpoint will not be listed in the Federation."
fi

# --------------------------------------------------------------
step "Selecting the local catalog backend"
# --------------------------------------------------------------
put LOCAL_CATALOG_BACKEND "$backend"

profiles=()
if [[ "$backend" == "mongodb" ]]; then
  # Provisioned by this repository's own compose file.
  profiles+=("mongodb")
  put CKAN_LOCAL_ENABLED "False"
  put MONGODB_CONNECTION_STRING "mongodb://mongodb:27017"
  ok "Using the bundled MongoDB (compose profile 'mongodb')"
else
  [[ -n "$ckan_url" ]]     || fail "--backend ckan requires --ckan-url (this installer does not provision CKAN yet)."
  [[ -n "$ckan_api_key" ]] || fail "--backend ckan requires --ckan-api-key."
  put CKAN_LOCAL_ENABLED "True"
  put CKAN_URL "$ckan_url"
  put CKAN_API_KEY "$ckan_api_key"
  ok "Using the CKAN at $ckan_url"
fi

if [[ "${fed_streaming:-false}" == "true" ]]; then
  profiles+=("kafka")
  info "Streaming enabled by the registration — adding the 'kafka' profile"
fi

# --------------------------------------------------------------
step "Rendering .env from example.env"
# --------------------------------------------------------------
env_path="$REPO_ROOT/.env"

if [[ -f "$env_path" && "$assume_yes" != "true" && "$dry_run" != "true" ]]; then
  read -r -p "$env_path already exists. Overwrite? [y/N] " reply
  [[ "$reply" =~ ^[Yy]$ ]] || fail "Aborted; nothing was changed."
fi

target="$env_path"
[[ "$dry_run" == "true" ]] && target="$(mktemp)"

python3 "$REPO_ROOT/install/render_env.py" \
  --example "$REPO_ROOT/example.env" \
  --overrides "$overrides_file" \
  --output "$target" \
  --strict \
  || fail "Could not render .env — an override does not match any variable documented in example.env."

ok "Wrote $target"

# --------------------------------------------------------------
step "Checking the configuration before starting anything"
# --------------------------------------------------------------
# Reading back what was written, rather than what was intended, so a rendering
# mistake surfaces here instead of at runtime.
auth_url="$(grep -E '^AUTH_API_URL=' "$target" | head -1 | cut -d= -f2- | tr -d '"')"

if [[ -n "$auth_url" ]]; then
  code="$(curl -s -o /dev/null -w '%{http_code}' -m 20 -X POST "$auth_url" \
    -H 'Content-Type: application/json' -d '{"token":"probe"}' || echo 000)"
  case "$code" in
    400|401|403) ok "Authentication service reachable at $auth_url (HTTP $code for an invalid token, as expected)" ;;
    000)         warn "Could not reach the authentication service at $auth_url — logins will fail until it is reachable." ;;
    *)           warn "Authentication service at $auth_url answered HTTP $code; expected 400/401/403 for an invalid token." ;;
  esac
fi

if [[ "$backend" == "ckan" ]]; then
  code="$(curl -s -o /dev/null -w '%{http_code}' -m 20 \
    -H "Authorization: $ckan_api_key" "${ckan_url%/}/api/3/action/site_read" || echo 000)"
  case "$code" in
    200) ok "CKAN reachable and the API key is accepted" ;;
    403|401) fail "CKAN at $ckan_url rejected the API key (HTTP $code). Fix the key before installing." ;;
    000) fail "Could not reach CKAN at $ckan_url." ;;
    *)   warn "CKAN at $ckan_url answered HTTP $code for site_read." ;;
  esac
fi

if [[ "$dry_run" == "true" ]]; then
  echo
  info "Dry run — rendered configuration follows, nothing was written or started:"
  echo "----------------------------------------------------------------"
  grep -vE '^\s*(#|$)' "$target" || true
  echo "----------------------------------------------------------------"
  rm -f "$target"
  exit 0
fi

# --------------------------------------------------------------
step "Starting the Endpoint"
# --------------------------------------------------------------
if [[ "$start" != "true" ]]; then
  info "--no-start given; bring it up yourself with:"
  echo "    cd $REPO_ROOT && EP_API_PORT=$ep_api_port ${COMPOSE[*]} ${profiles[*]/#/--profile } up -d"
  exit 0
fi

profile_args=()
for profile in "${profiles[@]:-}"; do
  [[ -n "$profile" ]] && profile_args+=(--profile "$profile")
done

cd "$REPO_ROOT"
EP_API_PORT="$ep_api_port" "${COMPOSE[@]}" "${profile_args[@]}" up -d

# --------------------------------------------------------------
step "Verifying the Endpoint answers"
# --------------------------------------------------------------
root_path="$(grep -E '^ROOT_PATH=' "$env_path" | head -1 | cut -d= -f2- | tr -d '"')"
health_url="http://localhost:${ep_api_port}${root_path}/health"

for attempt in $(seq 1 30); do
  code="$(curl -s -o /dev/null -w '%{http_code}' -m 5 "$health_url" || echo 000)"
  if [[ "$code" == "200" ]]; then
    ok "Endpoint healthy at $health_url"
    echo
    ok "Installed. UI: http://localhost:${ep_api_port}${root_path}/ui/"
    exit 0
  fi
  sleep 2
done

fail "The Endpoint did not become healthy at $health_url. Check: ${COMPOSE[*]} logs api"
