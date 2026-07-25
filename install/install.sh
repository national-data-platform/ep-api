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

CKAN_REPO_DEFAULT="https://github.com/sci-ndp/pop-ckan-docker.git"

config_id=""
federation_url="$FEDERATION_URL_DEFAULT"
backend="mongodb"
ckan_url=""
ckan_api_key=""
ckan_dir=""
ckan_repo="$CKAN_REPO_DEFAULT"
ckan_sysadmin=""
ckan_password=""
ckan_site_url=""
ckan_ssl_port="8443"
ckan_http_port="81"
ckan_app_port="5000"
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

banner() {
  echo
  echo "${BLUE}╭──────────────────────────────────────────────╮${NC}"
  echo "${BLUE}│${NC}    ${GREEN}NDP Endpoint — Configuration Assistant${NC}    ${BLUE}│${NC}"
  echo "${BLUE}╰──────────────────────────────────────────────╯${NC}"
  echo "  Sets up and starts an NDP Endpoint on this machine."
  echo "  Nothing is written or started until you confirm."
}

# section TITLE "explanation line" ["more explanation" ...]
# A titled heading followed by wrapped explanation lines, printed before the
# prompt(s) it introduces so each value comes with context.
section() {
  local title="$1"; shift
  echo
  echo "${BLUE}── ${GREEN}${title}${NC} ${BLUE}$(printf '%.0s─' $(seq 1 $((44 - ${#title}))))${NC}"
  local line
  for line in "$@"; do
    echo "  ${line}"
  done
}

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
  --ep-api-port <port>    Host port to publish the API on. Default: 8002

With --backend ckan, a CKAN is installed unless you point at one you already
have:
  --ckan-url <url>        Use this existing CKAN instead of installing one
  --ckan-api-key <key>    API key for that CKAN (required with --ckan-url)
  --ckan-dir <path>       Where to install CKAN. Default: <repo>/../ndp-ckan
  --ckan-repo <url>       Default: $CKAN_REPO_DEFAULT
  --ckan-sysadmin <name>  Sysadmin account to create. Default: ckan_admin
  --ckan-password <pass>  Its password. Default: a generated one
  --ckan-site-url <url>   How the Endpoint reaches CKAN. Default: https://<host-ip>:<ssl-port>
  --ckan-ssl-port <port>  CKAN's https port on the host. Default: 8443
  --ckan-http-port <port> CKAN's http port on the host. Default: 81
  --ckan-app-port <port>  CKAN's application port on the host. Default: 5000
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
    --ckan-dir)        ckan_dir="${2:-}"; shift 2 ;;
    --ckan-repo)       ckan_repo="${2:-}"; shift 2 ;;
    --ckan-sysadmin)   ckan_sysadmin="${2:-}"; shift 2 ;;
    --ckan-password)   ckan_password="${2:-}"; shift 2 ;;
    --ckan-site-url)   ckan_site_url="${2:-}"; shift 2 ;;
    --ckan-ssl-port)   ckan_ssl_port="${2:-}"; shift 2 ;;
    --ckan-http-port)  ckan_http_port="${2:-}"; shift 2 ;;
    --ckan-app-port)   ckan_app_port="${2:-}"; shift 2 ;;
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

banner

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
# Asking
# --------------------------------------------------------------
# Prompts are only used on a terminal. Under --yes, in CI or in the sandbox
# (docker exec without a tty) every answer falls back to its default, so
# automation never hangs waiting for input that will not come.
interactive() { [[ -t 0 && "$assume_yes" != "true" ]]; }

ask() {
  # ask VARIABLE "Question" "default"
  local __var="$1" __question="$2" __default="${3:-}" __reply=""
  if interactive; then
    read -r -p "  $__question${__default:+ [$__default]}: " __reply
  fi
  printf -v "$__var" '%s' "${__reply:-$__default}"
}

ask_secret() {
  local __var="$1" __question="$2" __reply=""
  if interactive; then
    read -r -s -p "  $__question: " __reply
    echo
  fi
  printf -v "$__var" '%s' "$__reply"
}

ask_yes_no() {
  # ask_yes_no VARIABLE "Question" yes|no
  local __var="$1" __question="$2" __default="$3" __reply=""
  if interactive; then
    local hint="[y/N]"
    [[ "$__default" == "yes" ]] && hint="[Y/n]"
    read -r -p "  $__question $hint: " __reply
  fi
  __reply="${__reply:-$__default}"
  case "$__reply" in
    [Yy]*) printf -v "$__var" '%s' "yes" ;;
    *)     printf -v "$__var" '%s' "no" ;;
  esac
}

choose() {
  # choose VARIABLE "Question" default_index "option one" "option two" ...
  local __var="$1" __question="$2" __default="$3"; shift 3
  local __options=("$@") __reply=""
  if interactive; then
    echo "  $__question"
    local index=1
    for option in "${__options[@]}"; do
      printf "    %d) %s\n" "$index" "$option"
      index=$((index + 1))
    done
    read -r -p "  Choice [$__default]: " __reply
  fi
  __reply="${__reply:-$__default}"
  [[ "$__reply" =~ ^[0-9]+$ ]] && [[ "$__reply" -ge 1 ]] && [[ "$__reply" -le ${#__options[@]} ]] \
    || __reply="$__default"
  printf -v "$__var" '%s' "$__reply"
}

port_free() {
  if (exec 3<>"/dev/tcp/127.0.0.1/$1") 2>/dev/null; then
    exec 3>&- 2>/dev/null || true
    return 1
  fi
  return 0
}

first_free_port() {
  # first_free_port STARTING_AT — so suggested defaults do not collide with
  # whatever the machine is already running.
  local candidate="$1"
  for _ in $(seq 1 50); do
    port_free "$candidate" && { echo "$candidate"; return; }
    candidate=$((candidate + 1))
  done
  echo "$1"
}

# --------------------------------------------------------------
# Helpers
# --------------------------------------------------------------
STATE_FILE="$REPO_ROOT/.env.install-state"

state_get() {
  [[ -f "$STATE_FILE" ]] || return 0
  grep -E "^$1=" "$STATE_FILE" 2>/dev/null | tail -n1 | cut -d= -f2- || true
}

state_set() {
  touch "$STATE_FILE"
  chmod 600 "$STATE_FILE"
  # Rewritten rather than appended so re-running does not accumulate stale
  # duplicates of the same key.
  python3 - "$STATE_FILE" "$1" "$2" <<'PY'
import sys
path, key, value = sys.argv[1], sys.argv[2], sys.argv[3]
lines = []
try:
    with open(path) as handle:
        lines = [line.rstrip("\n") for line in handle if not line.startswith(key + "=")]
except FileNotFoundError:
    pass
lines.append(f"{key}={value}")
with open(path, "w") as handle:
    handle.write("\n".join(lines) + "\n")
PY
}

set_env_kv() {
  # set_env_kv FILE KEY VALUE — set a key in a KEY=VALUE file, appending it if
  # absent. Used on CKAN's own .env: a blind sed would silently do nothing if
  # that project renamed or dropped the key, which is exactly how the previous
  # installer broke.
  python3 - "$1" "$2" "$3" <<'PY'
import re, sys
path, key, value = sys.argv[1], sys.argv[2], sys.argv[3]
with open(path) as handle:
    lines = handle.read().splitlines()
pattern = re.compile(rf"^#?\s*{re.escape(key)}=")
for index, line in enumerate(lines):
    if pattern.match(line):
        lines[index] = f"{key}={value}"
        break
else:
    lines.append(f"{key}={value}")
with open(path, "w") as handle:
    handle.write("\n".join(lines) + "\n")
PY
}

host_ip() {
  # The address the Endpoint container will use to reach CKAN, which is
  # published on the host rather than shared through a Docker network.
  ip route get 1.1.1.1 2>/dev/null | awk '{for (i=1;i<=NF;i++) if ($i=="src") {print $(i+1); exit}}' \
    || hostname -i 2>/dev/null | awk '{print $1}' \
    || echo "127.0.0.1"
}

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

# --------------------------------------------------------------
# Registering with the Federation
# --------------------------------------------------------------
register_with_federation() {
  # POST /ep/simple does more than record a row: it creates this Endpoint's
  # Keycloak client and group, fetches a staging-catalog token and registers
  # the Endpoint in Affinities. That is why registering is offered before
  # anything is installed — the configuration it returns then drives the rest
  # of the install exactly as a configuration id passed on the command line
  # would.
  local token userid poc ckan_user ckan_pass staging jhub streaming rexec public_ep
  local response http_code body

  echo
  echo "${BLUE}Registering with ${federation_url%/}${NC}"
  if [[ "$federation_url" == "$FEDERATION_URL_DEFAULT" ]]; then
    warn "This is the production Federation. Registering here creates a real"
    warn "Keycloak client and group. Use --federation-url to point elsewhere."
  fi

  section "Access token" \
    "Your personal NDP access token, from your user panel on the platform." \
    "It authorizes the registration and identifies you as the Endpoint's" \
    "administrator. It is sent only to the Federation, never stored."
  ask_secret token "Your NDP access token (not shown)"
  [[ -n "$token" ]] || fail "A token is required to register. Get one from your NDP user panel."

  # The Federation assigns the group's admin from this id, and it is the
  # subject of the very token being presented, so asking for it would only
  # invite a mismatch.
  userid="$(python3 - "$token" <<'PY'
import base64, json, sys
try:
    payload = sys.argv[1].split(".")[1]
    payload += "=" * (-len(payload) % 4)
    print(json.loads(base64.urlsafe_b64decode(payload)).get("sub", ""))
except Exception:
    print("")
PY
)"
  [[ -n "$userid" ]] || fail "Could not read a user id from that token — is it a complete access token?"
  ok "Registering as user $userid"

  section "Organization" \
    "The organization this Endpoint belongs to. Shown in its catalog and on" \
    "the platform."
  ask organization "Organization name" "${organization:-My-Organization}"

  section "Endpoint name" \
    "A short name identifying this Endpoint. Must be unique in the" \
    "Federation — registering fails if one already has this name."
  ask ep_name "Endpoint name" "${ep_name:-my_endpoint}"

  section "Contact email" \
    "The point of contact recorded for this Endpoint, for administrators to" \
    "reach whoever runs it."
  ask poc "Contact email" ""
  [[ -n "$poc" ]] || fail "A contact email is required to register."

  section "Catalog administrator" \
    "The administrator account created for this Endpoint's catalog. The same" \
    "credentials are reused if this script installs CKAN, so they match."
  ask ckan_user "Catalog admin username" "ckan_admin"
  ask_secret ckan_pass "Catalog admin password (not shown)"
  [[ -n "$ckan_pass" ]] || fail "A catalog admin password is required."

  section "Features" \
    "What this Endpoint offers. Each can be changed later; leave the" \
    "defaults if unsure."
  ask_yes_no public_ep "Publicly listed on the platform?" "yes"
  ask_yes_no staging   "Publish through a staging catalog first?" "no"
  ask_yes_no jhub      "Enable JupyterHub?" "no"
  ask_yes_no streaming "Enable data streaming (Kafka)?" "no"
  ask_yes_no rexec     "Enable remote execution?" "no"

  local payload
  payload="$(python3 - <<PY
import json
print(json.dumps({
    "ckan_name": "$ckan_user",
    "ckan_password": """$ckan_pass""",
    "enable_staging": $([[ "$staging" == "yes" ]] && echo true || echo false),
    "poc": "$poc",
    "organization": """$organization""",
    "jhub": $([[ "$jhub" == "yes" ]] && echo true || echo false),
    "streaming": $([[ "$streaming" == "yes" ]] && echo true || echo false),
    "rexec": $([[ "$rexec" == "yes" ]] && echo true || echo false),
    "ep_name": """$ep_name""",
    "userid": "$userid",
    "public": $([[ "$public_ep" == "yes" ]] && echo true || echo false),
}))
PY
)"

  echo
  echo "  About to register '${ep_name}' for '${organization}' at ${federation_url%/}."
  local proceed
  ask_yes_no proceed "Continue?" "yes"
  [[ "$proceed" == "yes" ]] || fail "Aborted; nothing was registered."

  response="$(mktemp)"
  http_code="$(curl -s -o "$response" -w '%{http_code}' -m 60 \
    -X POST "${federation_url%/}/ep/simple" \
    -H "Authorization: Bearer $token" \
    -H "Content-Type: application/json" \
    -d "$payload" || echo 000)"

  body="$(cat "$response")"
  rm -f "$response"

  case "$http_code" in
    201) ;;
    000) fail "Could not reach the Federation at ${federation_url%/}." ;;
    400) fail "The Federation rejected the registration: ${body}
       An Endpoint with this name may already exist." ;;
    401) fail "The Federation rejected the token. Check it has not expired." ;;
    422) fail "The Federation rejected the values: ${body}" ;;
    *)   fail "The Federation answered HTTP $http_code: ${body}" ;;
  esac

  config_id="$(python3 - "$body" <<'PY'
import json, sys
try:
    print(json.loads(sys.argv[1]).get("document_id", ""))
except Exception:
    print("")
PY
)"
  [[ -n "$config_id" ]] || fail "The Federation accepted the registration but returned no id: ${body}"

  ok "Registered. Configuration id: $config_id"
  # The catalog admin just chosen is reused when this installer provisions
  # CKAN, so the two agree rather than drifting apart.
  ckan_sysadmin="$ckan_user"
  ckan_password="$ckan_pass"
  echo
  info "Keep this id — re-running the installer with --config-id $config_id"
  info "reproduces this Endpoint without registering again."
}

# --------------------------------------------------------------
# Ask, when there is nobody to ask but the person running this.
# --------------------------------------------------------------
# A Federation registration answers most of these. Without one, and on a
# terminal, ask rather than silently installing a demo nobody asked for.
organization=""
ep_name=""
auth_api_url=""
oidc_issuer=""
oidc_client_id=""
want_oidc="no"

if [[ -z "$config_id" ]] && interactive; then
  echo
  echo "  A few questions, then nothing is written until you confirm."
  echo "  Press Enter to accept the value in brackets."

  section "Configuration id" \
    "Identifies this Endpoint's registration in the NDP Federation, the" \
    "central registry of all Endpoints. The registration holds the settings" \
    "the Endpoint runs with (organization, access group, catalog, identity" \
    "provider) and is what lists it on the platform." \
    "" \
    "Paste it if you already registered (on the platform or a previous run)." \
    "Leave blank and the next step offers to register now."
  ask config_id "Configuration id (blank to skip)" ""

  if [[ -z "$config_id" ]]; then
    section "Federation registration" \
      "Registering creates the configuration in the Federation and, with it," \
      "this Endpoint's Keycloak client and group — which is what makes" \
      "identity-provider sign-in possible without an administrator." \
      "Answer no to run a standalone Endpoint not listed in the Federation."
    ask_yes_no want_register "Register this Endpoint with the Federation now?" "yes"

    if [[ "$want_register" == "yes" ]]; then
      register_with_federation
    else
      already_warned="true"

      section "Organization" \
        "The organization this Endpoint belongs to. Shown in its catalog and" \
        "on the platform."
      ask organization "Organization name" "My-Organization"

      section "Endpoint name" \
        "A short name identifying this Endpoint. Used in its own labelling."
      ask ep_name "Endpoint name" "my_endpoint"
    fi
  fi

  section "Local catalog" \
    "Where this Endpoint stores the datasets published to it. MongoDB is" \
    "self-contained; CKAN is heavier but is the full NDP catalog."
  choose backend_choice "Where should this Endpoint store its catalog?" 1 \
    "MongoDB, installed alongside the Endpoint (simplest)" \
    "CKAN, installed by this script (takes several minutes)" \
    "CKAN, one I already have"
  case "$backend_choice" in
    1) backend="mongodb" ;;
    2) backend="ckan"; ckan_url="" ;;
    3) backend="ckan"
       section "Existing CKAN" \
         "Connect to a CKAN you already run. The key is verified before" \
         "anything is written."
       ask ckan_url       "CKAN URL" ""
       ask_secret ckan_api_key "CKAN API key (not shown)"
       ask ckan_sysadmin  "CKAN username that key belongs to (blank to skip verifying it)" ""
       ;;
  esac

  section "Endpoint port" \
    "The host port the Endpoint's web UI and API are served on. The default" \
    "is the first free port found, to avoid clashing with what is running."
  ep_api_port="$(first_free_port "$ep_api_port")"
  ask ep_api_port "Port to publish the Endpoint on" "$ep_api_port"

  if [[ "$backend" == "ckan" && -z "$ckan_url" ]]; then
    section "CKAN ports" \
      "The host ports the new CKAN is served on. Defaults are chosen from" \
      "what is free, since CKAN's own defaults (8443, 81, 5000) often clash."
    ckan_ssl_port="$(first_free_port "$ckan_ssl_port")"
    ckan_http_port="$(first_free_port "$ckan_http_port")"
    ckan_app_port="$(first_free_port "$ckan_app_port")"
    ask ckan_ssl_port  "CKAN https port"       "$ckan_ssl_port"
    ask ckan_http_port "CKAN http port"        "$ckan_http_port"
    ask ckan_app_port  "CKAN application port" "$ckan_app_port"
    ask ckan_sysadmin  "CKAN sysadmin to create" "ckan_admin"
  fi

  section "Authentication service" \
    "The AAI endpoint the Endpoint validates login tokens against. Keep the" \
    "default to authenticate against the National Data Platform."
  ask auth_api_url "Authentication service (AAI) URL" \
    "https://idp.nationaldataplatform.org/temp/information"

  section "Identity-provider sign-in" \
    "Optional. Adds a button that signs users in through the identity" \
    "provider's own page (CILogon, EarthScope, ORCID). Needs a client id" \
    "registered for this Endpoint; the Federation registration creates one." \
    "The access-token and username/password logins work either way."
  ask_yes_no want_oidc "Offer sign-in through the identity provider?" "no"
  if [[ "$want_oidc" == "yes" ]]; then
    ask oidc_issuer    "Identity provider realm URL" \
      "https://idp.nationaldataplatform.org/realms/NDP"
    ask oidc_client_id "Client id registered for this Endpoint" ""
    if [[ -z "$oidc_client_id" ]]; then
      warn "No client id: sign-in will stay off. See docs/configuration.md."
      want_oidc="no"
    fi
  fi
fi

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
elif [[ "${already_warned:-false}" != "true" ]]; then
  warn "No --config-id given: installing without a Federation registration."
  warn "The Endpoint will not be listed in the Federation."
fi

# --------------------------------------------------------------
step "Selecting the local catalog backend"
# --------------------------------------------------------------
# Answers given at the prompt. A Federation registration, where there is one,
# has already set organization and name, so these only fill in what it did not.
[[ -n "$organization" ]]  && put ORGANIZATION "$organization"
[[ -n "$ep_name" ]]       && put EP_NAME "$ep_name"
[[ -n "$auth_api_url" ]]  && put AUTH_API_URL "$auth_api_url"

if [[ "$want_oidc" == "yes" && -n "$oidc_client_id" ]]; then
  put OIDC_ENABLED "True"
  put OIDC_ISSUER "$oidc_issuer"
  put OIDC_CLIENT_ID "$oidc_client_id"
fi

put LOCAL_CATALOG_BACKEND "$backend"

profiles=()
if [[ "$backend" == "mongodb" ]]; then
  # Provisioned by this repository's own compose file.
  profiles+=("mongodb")
  put CKAN_LOCAL_ENABLED "False"
  put MONGODB_CONNECTION_STRING "mongodb://mongodb:27017"
  ok "Using the bundled MongoDB (compose profile 'mongodb')"
elif [[ -n "$ckan_url" ]]; then
  # Pointing at a CKAN that already exists.
  [[ -n "$ckan_api_key" ]] || fail "--ckan-url requires --ckan-api-key."
  put CKAN_LOCAL_ENABLED "True"
  put CKAN_URL "$ckan_url"
  put CKAN_API_KEY "$ckan_api_key"
  ok "Using the existing CKAN at $ckan_url"
else
  # Installing CKAN. It is a separate project with its own compose stack, so
  # it is cloned alongside this repository rather than into it.
  command -v git >/dev/null 2>&1 || fail "git is required to install CKAN."

  [[ -n "$ckan_dir" ]]       || ckan_dir="$(dirname "$REPO_ROOT")/ndp-ckan"
  [[ -n "$ckan_sysadmin" ]]  || ckan_sysadmin="$(state_get CKAN_SYSADMIN)"
  [[ -n "$ckan_sysadmin" ]]  || ckan_sysadmin="ckan_admin"
  [[ -n "$ckan_password" ]]  || ckan_password="$(state_get CKAN_PASSWORD)"
  [[ -n "$ckan_password" ]]  || ckan_password="$(python3 -c 'import secrets; print(secrets.token_urlsafe(18))')"
  [[ -n "$ckan_site_url" ]]  || ckan_site_url="https://$(host_ip):${ckan_ssl_port}"

  # Last chance to stop before anything is downloaded, built or written.
  if interactive; then
    echo
    echo "${BLUE}About to install CKAN:${NC}"
    echo "    into      $ckan_dir"
    echo "    reachable at $ckan_site_url"
    echo "    sysadmin  $ckan_sysadmin"
    echo "    ports     https $ckan_ssl_port, http $ckan_http_port, app $ckan_app_port"
    echo "  This pulls and builds several images and takes a few minutes."
    ask_yes_no proceed "Continue?" "yes"
    [[ "$proceed" == "yes" ]] || fail "Aborted; nothing was changed."
  fi

  saved_key="$(state_get CKAN_API_KEY)"
  saved_url="$(state_get CKAN_URL)"

  if [[ "$dry_run" == "true" && -z "$saved_key" ]]; then
    warn "--dry-run: CKAN would be installed at $ckan_dir and its token minted."
    warn "Nothing is installed; the rendered CKAN_API_KEY below is a placeholder."
    ckan_api_key="(minted during a real install)"
  elif [[ -n "$saved_key" && -n "$saved_url" ]] && curl -sk -o /dev/null -m 10 "$saved_url"; then
    ok "CKAN already installed and reachable at $saved_url — reusing its API key"
    ckan_site_url="$saved_url"
    ckan_api_key="$saved_key"
  else
    step "Installing CKAN"

    if [[ ! -d "$ckan_dir/.git" ]]; then
      info "Cloning $ckan_repo into $ckan_dir"
      git clone --depth 1 "$ckan_repo" "$ckan_dir" \
        || fail "Could not clone the CKAN repository."
    else
      info "CKAN checkout already present at $ckan_dir"
    fi

    [[ -f "$ckan_dir/.env" ]] || {
      [[ -f "$ckan_dir/.env.example" ]] \
        || fail "$ckan_dir has no .env.example — the CKAN project's layout has changed."
      cp "$ckan_dir/.env.example" "$ckan_dir/.env"
    }

    set_env_kv "$ckan_dir/.env" CKAN_SYSADMIN_NAME "$ckan_sysadmin"
    set_env_kv "$ckan_dir/.env" CKAN_SYSADMIN_PASSWORD "$ckan_password"
    set_env_kv "$ckan_dir/.env" CKAN_SITE_URL "$ckan_site_url"
    set_env_kv "$ckan_dir/.env" NGINX_SSLPORT_HOST "$ckan_ssl_port"
    set_env_kv "$ckan_dir/.env" NGINX_PORT_HOST "$ckan_http_port"
    set_env_kv "$ckan_dir/.env" CKAN_PORT_HOST "$ckan_app_port"
    ok "Configured CKAN for $ckan_site_url (sysadmin: $ckan_sysadmin)"

    # Compose reports a port clash only after pulling and building, which on
    # CKAN is several minutes of work before the failure appears. Checking
    # first turns that into an immediate, actionable message.
    for entry in "https:$ckan_ssl_port" "http:$ckan_http_port" "app:$ckan_app_port"; do
      label="${entry%%:*}"; port="${entry##*:}"
      if (exec 3<>"/dev/tcp/127.0.0.1/$port") 2>/dev/null; then
        exec 3>&- 2>/dev/null || true
        holder="$(docker ps --format '{{.Names}}\t{{.Ports}}' | awk -v p=":$port->" '$0 ~ p {print $1; exit}')"
        fail "Port $port (CKAN $label) is already in use${holder:+ by container '$holder'}.
       Choose another with --ckan-${label/https/ssl}-port, or stop what is using it."
      fi
    done
    ok "Ports $ckan_ssl_port, $ckan_http_port and $ckan_app_port are free"

    info "Building and starting CKAN — this takes several minutes the first time"
    (cd "$ckan_dir" && "${COMPOSE[@]}" up -d --build) \
      || fail "CKAN failed to start. Inspect it with: cd $ckan_dir && ${COMPOSE[*]} logs"

    step "Waiting for CKAN to become ready"
    ckan_cid=""
    for attempt in $(seq 1 120); do
      ckan_cid="$(cd "$ckan_dir" && "${COMPOSE[@]}" ps -q ckan 2>/dev/null | head -n1)"
      if [[ -n "$ckan_cid" ]]; then
        health="$(docker inspect -f '{{if .State.Health}}{{.State.Health.Status}}{{else}}{{.State.Status}}{{end}}' "$ckan_cid" 2>/dev/null || echo starting)"
        [[ "$health" == "healthy" || "$health" == "running" ]] && break
      fi
      [[ $attempt -eq 120 ]] && fail "CKAN did not become ready. Inspect: cd $ckan_dir && ${COMPOSE[*]} logs ckan"
      sleep 5
    done
    ok "CKAN is up"

    step "Minting a CKAN API token"
    ckan_ini="$(docker exec "$ckan_cid" bash -c '
      for path in /srv/app/ckan.ini /etc/ckan/ckan.ini /etc/ckan/default/ckan.ini; do
        [ -f "$path" ] && { echo "$path"; exit 0; }
      done
      exit 1' 2>/dev/null)" \
      || fail "Could not locate ckan.ini inside the CKAN container."

    # CKAN prints the token amid other output; the token itself is a JWT.
    ckan_api_key="$(docker exec "$ckan_cid" \
      bash -c "ckan -c '$ckan_ini' user token add '$ckan_sysadmin' ep_installer" 2>/dev/null \
      | tr -cd '\11\12\15\40-\176' | grep -Eo 'eyJ[0-9a-zA-Z._-]{30,}' | head -n1)"

    if [[ -z "$ckan_api_key" ]]; then
      warn "Could not read a token from CKAN. Its output was:"
      docker exec "$ckan_cid" bash -c "ckan -c '$ckan_ini' user token add '$ckan_sysadmin' ep_installer" >&2 || true
      fail "CKAN did not return an API token."
    fi

    state_set CKAN_API_KEY "$ckan_api_key"
    state_set CKAN_URL "$ckan_site_url"
    state_set CKAN_SYSADMIN "$ckan_sysadmin"
    state_set CKAN_PASSWORD "$ckan_password"
    ok "Token minted and saved to $(basename "$STATE_FILE") so re-running does not create another"
  fi

  put CKAN_LOCAL_ENABLED "True"
  put CKAN_URL "$ckan_site_url"
  put CKAN_API_KEY "$ckan_api_key"
  # CKAN is served over https with a self-signed certificate.
  put CKAN_VERIFY_SSL "False"
  ckan_url="$ckan_site_url"
fi

if [[ "${fed_streaming:-false}" == "true" ]]; then
  profiles+=("kafka")
  info "Streaming enabled by the registration — adding the 'kafka' profile"
fi

# --------------------------------------------------------------
step "Rendering .env from example.env"
# --------------------------------------------------------------
env_path="$REPO_ROOT/.env"

if [[ -f "$env_path" && "$dry_run" != "true" ]]; then
  # Always keep a copy, including with --yes. A .env holds credentials that
  # exist nowhere else — it is git-ignored, so an overwrite is unrecoverable
  # unless something saved it first. Automation must not be able to destroy it.
  backup="$env_path.backup.$(date +%Y%m%d-%H%M%S)"
  cp -p "$env_path" "$backup"
  chmod 600 "$backup"
  warn "Existing .env saved to $(basename "$backup")"

  if [[ "$assume_yes" != "true" ]]; then
    read -r -p "$env_path already exists. Overwrite? [y/N] " reply
    [[ "$reply" =~ ^[Yy]$ ]] || fail "Aborted; nothing was changed (backup kept at $backup)."
  fi
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

if [[ "$backend" == "ckan" && "$dry_run" != "true" ]]; then
  # -k throughout: a freshly installed CKAN serves https with a self-signed
  # certificate, which is why CKAN_VERIFY_SSL is False above.

  # Reachability first, so an unreachable CKAN is not reported as a bad key.
  code="$(curl -sk -o /dev/null -w '%{http_code}' -m 20 \
    "${ckan_url%/}/api/3/action/status_show" || echo 000)"
  case "$code" in
    200) ok "CKAN reachable at $ckan_url" ;;
    000) fail "Could not reach CKAN at $ckan_url." ;;
    *)   fail "CKAN at $ckan_url answered HTTP $code — it does not look like a working CKAN API." ;;
  esac

  # Then the key itself. api_token_list is used because it actually
  # discriminates: it answers 200 for a valid token and 403 for a missing or
  # invalid one. Most read actions answer 200 to anonymous callers, so they
  # would pass with any string at all and prove nothing.
  if [[ -n "$ckan_sysadmin" ]]; then
    code="$(curl -sk -o /dev/null -w '%{http_code}' -m 20 \
      -H "Authorization: $ckan_api_key" \
      "${ckan_url%/}/api/3/action/api_token_list?user=${ckan_sysadmin}" || echo 000)"
    case "$code" in
      200)     ok "CKAN accepted the API key" ;;
      401|403) fail "CKAN at $ckan_url rejected the API key (HTTP $code)." ;;
      *)       warn "Could not confirm the CKAN API key (HTTP $code)." ;;
    esac
  else
    warn "CKAN key not verified: pass --ckan-sysadmin <name> to check it against this CKAN."
  fi
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

if (exec 3<>"/dev/tcp/127.0.0.1/$ep_api_port") 2>/dev/null; then
  exec 3>&- 2>/dev/null || true
  holder="$(docker ps --format '{{.Names}}\t{{.Ports}}' | awk -v p=":$ep_api_port->" '$0 ~ p {print $1; exit}')"
  fail "Port $ep_api_port is already in use${holder:+ by container '$holder'}.
       Choose another with --ep-api-port, or stop what is using it."
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
