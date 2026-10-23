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

REPO_URL_DEFAULT="https://github.com/national-data-platform/ep-api.git"

# --------------------------------------------------------------
# Bootstrap: work whether run from a checkout or piped from the web.
# --------------------------------------------------------------
# The installer needs the rest of the repository next to it (example.env,
# docker-compose.yml, the render helper). When run as
#   bash <(curl -fsSL .../install/install.sh) ...
# there is no checkout, so clone the repository and re-exec from there.
# When run from a checkout, this is skipped and it runs in place.
_script="${BASH_SOURCE[0]:-$0}"
_here=""
if [[ "$_script" != /dev/fd/* && "$_script" != /proc/self/fd/* && -f "$_script" ]]; then
  _here="$(cd "$(dirname "$_script")/.." 2>/dev/null && pwd || true)"
fi

# status, stop, start and uninstall act on an Endpoint already installed
# (issue #372). Piped from the web they run against its checkout as it is:
# nothing is fetched, and the checkout is not moved to another version.
case "${1:-}" in
  status|stop|start|uninstall)
    if [[ -z "$_here" || ! -f "$_here/example.env" ]]; then
      _instance=""
      _args=("$@")
      for ((_i = 0; _i < ${#_args[@]}; _i++)); do
        [[ "${_args[$_i]}" == "--instance" ]] && _instance="${_args[$((_i + 1))]:-}"
      done
      if [[ -n "$_instance" && "$_instance" != "ndp" ]]; then
        _here="${EP_INSTALL_DIR:-$HOME/ndp-ep-$_instance}"
      else
        _here="${EP_INSTALL_DIR:-$HOME/ndp-ep}"
      fi
      if [[ ! -f "$_here/example.env" ]]; then
        echo "No Endpoint installed at $_here (set EP_INSTALL_DIR, or --instance <name>)." >&2
        exit 1
      fi
    fi ;;
esac

if [[ -z "$_here" || ! -f "$_here/example.env" ]]; then
  echo "==> Fetching the NDP Endpoint repository"
  command -v git >/dev/null 2>&1 || { echo "git is required to install. Please install git and retry." >&2; exit 1; }
  repo_url="${EP_REPO_URL:-$REPO_URL_DEFAULT}"
  # A named instance (--instance, issue #355) gets a checkout of its own, so
  # a second Endpoint on the host does not reuse -- and reconfigure -- the
  # first one's.
  _instance=""
  _ref=""
  _args=("$@")
  for ((_i = 0; _i < ${#_args[@]}; _i++)); do
    [[ "${_args[$_i]}" == "--instance" ]] && _instance="${_args[$((_i + 1))]:-}"
    [[ "${_args[$_i]}" == "--ref" ]] && _ref="${_args[$((_i + 1))]:-}"
  done

  # Which version to install (issue #371). It was main, so the same command
  # installed a different program from one week to the next, and a bad push
  # reached every new installation at once. Now the newest release tag
  # (vX.Y.Z; pre-releases are not offered) unless --ref, then EP_REPO_REF --
  # which the platform's setup.sh sets to pin one -- say otherwise.
  repo_ref="${_ref:-${EP_REPO_REF:-}}"
  if [[ -n "$repo_ref" ]]; then
    echo "    Installer version: $repo_ref"
  else
    if ! _tags="$(git ls-remote --tags --refs "$repo_url" 'v*' 2>/dev/null)"; then
      echo "Could not list the releases of $repo_url. Check the network, or name a" >&2
      echo "version with --ref <tag> (or --ref main for the development version)." >&2
      exit 1
    fi
    repo_ref="$(printf '%s\n' "$_tags" | sed -n 's|.*refs/tags/||p' \
      | grep -E '^v[0-9]+\.[0-9]+\.[0-9]+$' | sort -V | tail -n1 || true)"
    if [[ -n "$repo_ref" ]]; then
      echo "    Installer version: $repo_ref (latest release)"
    else
      repo_ref="main"
      echo "    $repo_url has no release; installing main, the development version." >&2
      echo "    Installer version: main"
    fi
  fi
  if [[ -n "$_instance" && "$_instance" != "ndp" ]]; then
    target="${EP_INSTALL_DIR:-$HOME/ndp-ep-$_instance}"
  else
    target="${EP_INSTALL_DIR:-$HOME/ndp-ep}"
  fi

  if [[ -d "$target/.git" ]]; then
    echo "    Reusing existing checkout at $target"
    # FETCH_HEAD is what was just fetched, whether $repo_ref names a tag or a
    # branch. Checking the ref out by name does not work for a tag: a shallow
    # fetch leaves it in FETCH_HEAD without writing refs/tags/, and
    # "origin/<tag>" never existed at all, that namespace being for branches.
    # Both commands failed, "|| true" hid it, and the run carried on against
    # whatever was already there -- so re-running after an upgrade silently
    # reinstalled the version the machine had seen first (issue #295).
    if ! { git -C "$target" fetch --depth 1 origin "$repo_ref" >/dev/null 2>&1 \
           && git -C "$target" checkout -q --detach FETCH_HEAD; }; then
      # Starting again rather than carrying on: a checkout that cannot be
      # moved to the requested version is not one worth reusing.
      echo "    Could not update it to $repo_ref — cloning again" >&2
      rm -rf "$target"
    fi
  fi

  if [[ ! -d "$target/.git" ]]; then
    echo "    Cloning $repo_url ($repo_ref) into $target"
    git clone --depth 1 --branch "$repo_ref" "$repo_url" "$target" \
      || { echo "Could not clone $repo_url" >&2; exit 1; }
  fi

  echo "    Running the installer from $target"
  exec bash "$target/install/install.sh" "$@"
fi

REPO_ROOT="$_here"
FEDERATION_URL_DEFAULT="https://federation.ndp.utah.edu"
FEDERATION_URL_TEST="https://federation.ndp.utah.edu/test"

CKAN_REPO_DEFAULT="https://github.com/sci-ndp/pop-ckan-docker.git"

config_id=""
federation_url="$FEDERATION_URL_DEFAULT"
# Set by --federation-url, so --env cannot overrule a URL that was asked for
# by name. The platform sends both, and the script it replaces resolved them
# in this order (issue #285).
federation_url_explicit="false"
federation_env=""
# The lightest Endpoint there is: no catalog to install, nothing to store, and
# every optional integration off. It authenticates users, searches the
# platform's global catalog and reports to the Federation. Asking for MongoDB
# or CKAN is opting in to more.
backend="none"
mongodb_url=""
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
# Set when the operator chose the CKAN ports (flags or prompts), which a named
# instance then keeps instead of picking its own (issue #357).
ckan_ports_given="false"
ep_api_port="8002"
# The name of this Endpoint on the host. "ndp", the default, keeps the
# container names and published ports a single Endpoint has always had; any
# other name lets a further Endpoint run next to it (issue #355).
instance=""
want_access_requests="no"
# NetBird and Affinities, both opt-in (issue #359). Empty means "as the last
# run of this checkout left it", which the install state remembers, so a
# re-run -- an upgrade -- keeps them without the flags or the setup key.
want_netbird=""
netbird_management_url=""
netbird_setup_key_file=""
# The owner's NDP access token, read from a file for unattended runs; with it
# the NetBird setup key comes from the Federation (issue #361).
ndp_token_file=""
want_affinities=""
# S3 object storage. want_s3 turns it on; with no s3_endpoint the bundled MinIO
# is installed (compose profile 's3'), otherwise the Endpoint points at the
# S3-compatible service given here. s3_secure controls https to that service.
want_s3="no"
s3_endpoint=""
s3_access_key=""
s3_secret_key=""
s3_region="us-east-1"
s3_secure="False"
dry_run="false"
start="true"
assume_yes="false"
# The Federation has no field for a remote-execution URL, so when registration
# captures one it is applied straight to the .env after the config is fetched.
reg_rexec_url=""
# Where this run is recorded (issue #374). Empty means install.log next to the
# checkout; /dev/null turns the record off. log_active is set once it is open.
log_file=""
log_active=""
# How long one "docker compose up --build" may take before the run gives up
# (issue #376): minutes, or seconds with an "s" suffix; 0 means no limit.
compose_timeout="30"
# status | stop | start | uninstall (issue #372); empty means install.
subcommand=""
remove_data="false"

RED=$'\033[0;31m'; GREEN=$'\033[0;32m'; YELLOW=$'\033[1;33m'
BLUE=$'\033[0;34m'; NC=$'\033[0m'

info()    { echo "${BLUE}[info]${NC} $*"; }
ok()      { echo "${GREEN}[ ok ]${NC} $*"; }
warn()    { echo "${YELLOW}[warn]${NC} $*" >&2; }
fail()    {
  echo "${RED}[fail]${NC} $*" >&2
  [[ -n "$log_active" ]] && echo "       install log: $log_active" >&2
  exit 1
}
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
  # From the web (clones the latest release, then installs; --ref for another):
  bash <(curl -fsSL https://raw.githubusercontent.com/national-data-platform/ep-api/main/install/install.sh) [options]

  # From a checkout:
  install.sh --config-id <id> [options]
  install.sh --backend mongodb [options]        # standalone, no Federation

  # An installed Endpoint (from its checkout, or from the web as above):
  install.sh status | stop | start [--instance <name>]
  install.sh uninstall [--remove-data] [--yes] [--instance <name>]

Commands:
  status                  What is installed and running: instance, Compose
                          project, version, catalog, containers, port, health,
                          NetBird. Changes nothing.
  stop, start             Stop or start this Endpoint's containers (and the
                          CKAN the installer set up for it) as they are, on
                          the ports they were created with.
  uninstall               Remove this Endpoint's containers and networks and
                          the .env backups (old credentials). Its data, .env
                          and install state are kept unless --remove-data,
                          which also deletes its volumes. Asks first; --yes
                          when nobody can answer. The checkout and NetBird
                          are left in place.

Options:
  --config-id <id>        Federation configuration id for this Endpoint.
                          --config_id is accepted too: it is what the
                          platform's create-endpoint page sends.
  --federation-url <url>  Default: $FEDERATION_URL_DEFAULT
                          --federation_url is accepted too.
  --env prod|test         Pick the Federation by name instead of by URL.
                          prod: $FEDERATION_URL_DEFAULT
                          test: $FEDERATION_URL_TEST
                          Ignored when --federation-url is given.
  --backend <name>        Local catalog backend: none | mongodb | ckan.
                          Default: none
  --ep-api-port <port>    Host port to publish the API on. Default: 8002
  --instance <name>       Run this Endpoint next to others on the same host:
                          its containers are named <name>-…, the bundled
                          services get free host ports, and from the web it
                          installs into ~/ndp-ep-<name>. Lowercase letters,
                          digits and '-'. Default: ndp (a single Endpoint).
  --access-requests       Let users request access and admins approve it.
                          Stored in MongoDB: one is installed unless the
                          catalog already provides one.
  --s3                    Enable S3 object storage. Installs the bundled MinIO
                          (compose profile 's3') unless --s3-endpoint points at
                          an S3-compatible service you already run.
  --s3-endpoint <host>    Use this existing S3 service instead of installing
                          MinIO (e.g. s3.amazonaws.com or my-host:9000).
  --s3-access-key <key>   Access key for that S3 (required with --s3-endpoint).
  --s3-secret-key <key>   Secret key for that S3 (required with --s3-endpoint).
  --s3-region <region>    Region for that S3. Default: us-east-1
  --s3-secure             Use https to reach that S3 (default is http).
  --netbird               Join this machine to NDP's NetBird network. Installs
                          the NetBird client on the host if missing (needs
                          sudo); the management URL comes from the Federation
                          configuration. Kept on re-runs. A new installation
                          joins without it, but carries on, saying why, when
                          it cannot; with --netbird it stops instead.
  --no-netbird            Do not join NetBird. Kept on re-runs.
  --netbird-setup-key-file <path>
                          File holding the NetBird setup key (implies
                          --netbird). Without it the key is fetched from the
                          Federation with your NDP access token (see
                          --ndp-token-file), or asked for, hidden. Never
                          written anywhere. Not needed once connected.
  --ndp-token-file <path> File holding your NDP access token, for unattended
                          runs; otherwise it is asked for, hidden. Never
                          written anywhere.
  --netbird-management-url <url>
                          Override the management URL the Federation gives.
  --affinities            Turn on the Affinities integration, with the
                          Affinities URL and this Endpoint's Affinities id from
                          the Federation configuration. Kept on re-runs.

With --backend none nothing is stored locally and no catalog is installed. The
Endpoint authenticates users, searches the platform's global catalog and
reports to the Federation. It is the quickest Endpoint to stand up.

With --backend mongodb, the bundled MongoDB is started unless you point at one
you already have:
  --mongodb-url <url>     Use this existing MongoDB instead of starting one

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
  --ref <tag|branch>      From the web: install this version instead of the
                          latest release (e.g. v0.34.61, or main for the
                          development version). EP_REPO_REF does the same.
  --log-file <path>       Append this run to <path>. Default: install.log in
                          the checkout. /dev/null keeps no log.
  --compose-timeout <n>   Give up when building and starting a stack takes
                          longer than <n> minutes (or <n>s seconds). Default:
                          30. 0 means no limit.
  -h, --help              This message

The configuration id comes from registering the Endpoint with the Federation.
Values it supplies (organization, groups, streaming, staging catalog, identity
provider) are applied on top of the documented defaults in example.env.
USAGE
}

# As given, for the install log; the secrets among them are masked there.
cli_args=("$@")

case "${1:-}" in
  status|stop|start|uninstall) subcommand="$1"; shift ;;
esac

while [[ $# -gt 0 ]]; do
  case "$1" in
    # The underscore spellings are what the platform's "create endpoint"
    # page sends, and --env is how it selects the test federation. They are
    # accepted so this installer is a drop-in for the script that page used
    # to call; the hyphenated spellings remain the documented ones (#285).
    --config-id|--config_id)
                       config_id="${2:-}"; shift 2 ;;
    --federation-url|--federation_url)
                       federation_url="${2:-}"
                       federation_url_explicit="true"; shift 2 ;;
    --env)             federation_env="${2:-}"; shift 2 ;;
    --backend)         backend="${2:-}"; shift 2 ;;
    --mongodb-url)     mongodb_url="${2:-}"; shift 2 ;;
    --ckan-url)        ckan_url="${2:-}"; shift 2 ;;
    --ckan-api-key)    ckan_api_key="${2:-}"; shift 2 ;;
    --ckan-dir)        ckan_dir="${2:-}"; shift 2 ;;
    --ckan-repo)       ckan_repo="${2:-}"; shift 2 ;;
    --ckan-sysadmin)   ckan_sysadmin="${2:-}"; shift 2 ;;
    --ckan-password)   ckan_password="${2:-}"; shift 2 ;;
    --ckan-site-url)   ckan_site_url="${2:-}"; shift 2 ;;
    --ckan-ssl-port)   ckan_ssl_port="${2:-}"; ckan_ports_given="true"; shift 2 ;;
    --ckan-http-port)  ckan_http_port="${2:-}"; ckan_ports_given="true"; shift 2 ;;
    --ckan-app-port)   ckan_app_port="${2:-}"; ckan_ports_given="true"; shift 2 ;;
    --ep-api-port)     ep_api_port="${2:-}"; shift 2 ;;
    --instance)        instance="${2:-}"; shift 2 ;;
    --access-requests) want_access_requests="yes"; shift ;;
    --s3)              want_s3="yes"; shift ;;
    --s3-endpoint)     want_s3="yes"; s3_endpoint="${2:-}"; shift 2 ;;
    --s3-access-key)   s3_access_key="${2:-}"; shift 2 ;;
    --s3-secret-key)   s3_secret_key="${2:-}"; shift 2 ;;
    --s3-region)       s3_region="${2:-}"; shift 2 ;;
    --s3-secure)       s3_secure="True"; shift ;;
    --netbird)         want_netbird="yes"; shift ;;
    --no-netbird)      want_netbird="no"; shift ;;
    --netbird-setup-key-file) netbird_setup_key_file="${2:-}"; want_netbird="yes"; shift 2 ;;
    --netbird-management-url) netbird_management_url="${2:-}"; shift 2 ;;
    --ndp-token-file)  ndp_token_file="${2:-}"; shift 2 ;;
    --affinities)      want_affinities="yes"; shift ;;
    --dry-run)         dry_run="true"; shift ;;
    --no-start)        start="false"; shift ;;
    --yes)             assume_yes="true"; shift ;;
    --log-file)        log_file="${2:-}"; shift 2 ;;
    # Chooses the version when installing from the web; the bootstrap above
    # has already acted on it, and a checkout runs what it has.
    --ref)             shift 2 ;;
    --compose-timeout) compose_timeout="${2-}"; shift 2 ;;
    --remove-data)     remove_data="true"; shift ;;
    -h|--help)         usage; exit 0 ;;
    *)                 fail "Unknown option: $1 (try --help)" ;;
  esac
done

case "$federation_env" in
  "")   ;;
  prod) [[ "$federation_url_explicit" == "true" ]] || federation_url="$FEDERATION_URL_DEFAULT" ;;
  test) [[ "$federation_url_explicit" == "true" ]] || federation_url="$FEDERATION_URL_TEST" ;;
  *)    fail "--env must be prod or test (got: $federation_env)" ;;
esac

[[ "$backend" == "none" || "$backend" == "mongodb" || "$backend" == "ckan" ]] \
  || fail "--backend must be none, mongodb or ckan (got: $backend)"

[[ "$compose_timeout" =~ ^[0-9]+s?$ ]] \
  || fail "--compose-timeout must be a number of minutes, or of seconds ending in s (got: '$compose_timeout')"

# --------------------------------------------------------------
# The install log (issue #374)
# --------------------------------------------------------------
# Everything the run prints is also appended to a file, so a run that fails
# unattended, or ten minutes in, leaves a record of what it was asked to do and
# where it stopped. Appended, not truncated: a failed attempt and the retry
# that followed are both kept. The terminal sees exactly what it did before.
finish_log() { :; }
[[ -n "$log_file" ]] || log_file="$REPO_ROOT/install.log"
if [[ "$log_file" != "/dev/null" ]]; then
  if ( umask 077; : >> "$log_file" ) 2>/dev/null; then
    chmod 600 "$log_file" 2>/dev/null || true
    shown_args=()
    for ((_i = 0; _i < ${#cli_args[@]}; _i++)); do
      shown_args+=("$(printf '%q' "${cli_args[$_i]}")")
      case "${cli_args[$_i]}" in
        --ckan-password|--ckan-api-key|--s3-access-key|--s3-secret-key)
          if ((_i + 1 < ${#cli_args[@]})); then
            shown_args+=("***"); _i=$((_i + 1))
          fi ;;
      esac
    done
    {
      echo
      echo "=== $(date -u '+%Y-%m-%dT%H:%M:%SZ') install.sh run"
      echo "    version: $(git -C "$REPO_ROOT" describe --tags --always 2>/dev/null || echo unknown)"
      echo "    args: ${shown_args[*]}"
      echo "    user: $(id -un 2>/dev/null || echo unknown)@$(hostname 2>/dev/null || echo unknown)"
      echo "    federation: $federation_url"
    } >> "$log_file"
    exec 5>&1 6>&2
    exec > >(tee -a "$log_file")
    log_out_pid=$!
    exec 2> >(tee -a "$log_file" >&6)
    log_err_pid=$!
    log_active="$log_file"
    # On the way out: hand the terminal back, let both copies finish writing,
    # then strip the colour codes, which only make sense on a terminal.
    finish_log() {
      [[ -n "$log_active" ]] || return 0
      exec 1>&5 2>&6
      # Bounded: a daemon started during the run could still hold the pipe,
      # and the record is not worth hanging the exit for.
      local _w
      for _w in $(seq 1 50); do
        kill -0 "$log_out_pid" 2>/dev/null || kill -0 "$log_err_pid" 2>/dev/null || break
        sleep 0.1
      done
      sed -i 's/\x1b\[[0-9;]*m//g' "$log_active" 2>/dev/null || true
      log_active=""
    }
    trap finish_log EXIT
  else
    warn "Cannot write the install log at $log_file; carrying on without it."
  fi
fi

# --------------------------------------------------------------
# status, stop, start, uninstall (issue #372)
# --------------------------------------------------------------
# They act on the Endpoint this checkout holds, through the labels Compose puts
# on its containers, volumes and networks, so neither its port nor its profiles
# have to be remembered. The install state says what the installer set up.
lc_state() {
  [[ -f "$REPO_ROOT/.env.install-state" ]] || return 0
  grep -E "^$1=" "$REPO_ROOT/.env.install-state" | tail -n1 | cut -d= -f2- || true
}

lc_env() {
  [[ -f "$REPO_ROOT/.env" ]] || return 0
  grep -E "^$1=" "$REPO_ROOT/.env" | tail -n1 | cut -d= -f2- | sed 's/^"\(.*\)"$/\1/' || true
}

lc_project() {
  local project
  project="$(lc_env COMPOSE_PROJECT_NAME)"
  if [[ -z "$project" && "$lc_instance" != "ndp" ]]; then
    project="ndp-ep-$lc_instance"
  fi
  # Compose's own default: the checkout's directory name.
  [[ -n "$project" ]] || project="$(basename "$REPO_ROOT" | tr '[:upper:]' '[:lower:]' | tr -cd 'a-z0-9_-')"
  printf '%s' "$project"
}

# The CKAN this installer set up for the Endpoint, if any: recorded since
# 0.34.63, otherwise where the installer puts it by default.
lc_ckan_dir() {
  local dir
  dir="$(lc_state CKAN_DIR)"
  if [[ -z "$dir" && -n "$(lc_state CKAN_URL)" ]]; then
    if [[ "$lc_instance" != "ndp" ]]; then
      dir="$(dirname "$REPO_ROOT")/ndp-ckan-$lc_instance"
    else
      dir="$(dirname "$REPO_ROOT")/ndp-ckan"
    fi
  fi
  [[ -n "$dir" && -f "$dir/docker-compose.yml" ]] && printf '%s' "$dir"
  return 0
}

lc_containers() {
  # lc_containers [-a] -- ids of the project's (running, or all) containers
  docker ps -q "$@" --filter "label=com.docker.compose.project=$lc_project" 2>/dev/null || true
}

lc_port() {
  local port
  port="$(docker port "${lc_instance}-ep-api" 80 2>/dev/null | head -n1 | sed 's/.*://')"
  [[ -n "$port" ]] || port="$(lc_state EP_API_PORT)"
  printf '%s' "$port"
}

lc_status() {
  local running all port health_url code nb ip version
  version="$(lc_state INSTALLER_VERSION)"
  [[ -n "$version" ]] || version="$(git -C "$REPO_ROOT" describe --tags --always 2>/dev/null || echo unknown)"
  running="$(lc_containers | grep -c . || true)"
  all="$(lc_containers -a | grep -c . || true)"
  port="$(lc_port)"
  echo "Endpoint at $REPO_ROOT"
  echo "  instance: $lc_instance"
  echo "  compose project: $lc_project"
  echo "  version: $version"
  echo "  catalog: $(lc_env LOCAL_CATALOG_BACKEND)"
  echo "  containers: $running running of $all"
  echo "  port: ${port:-unknown}"
  if [[ -n "$port" ]]; then
    health_url="http://localhost:${port}$(lc_env ROOT_PATH)/health"
    code="$(curl -s -o /dev/null -w '%{http_code}' -m 5 "$health_url" || true)"
    if [[ "$code" == "200" ]]; then
      echo "  health: healthy at $health_url"
    else
      echo "  health: not answering at $health_url"
    fi
  fi
  if ! command -v netbird >/dev/null 2>&1; then
    echo "  NetBird: client not installed"
  else
    nb="$(netbird status --json 2>/dev/null || true)"
    if [[ "$nb" =~ \"connected\":[[:space:]]*true ]]; then
      ip="$(sed -n 's/.*"netbirdIp":[[:space:]]*"\([^"/]*\).*/\1/p' <<< "$nb")"
      echo "  NetBird: connected${ip:+ ($ip)}"
    else
      echo "  NetBird: not connected"
    fi
  fi
  local ckan; ckan="$(lc_ckan_dir)"
  [[ -z "$ckan" ]] || echo "  CKAN: $ckan"
}

lc_stop() {
  local ids ckan
  ids="$(lc_containers | tr '\n' ' ' | sed 's/ *$//')"
  if [[ -z "$ids" ]]; then
    ok "Endpoint '$lc_instance' is already stopped."
  else
    # shellcheck disable=SC2086
    docker stop $ids >/dev/null
    ok "Stopped Endpoint '$lc_instance' (Compose project $lc_project)."
  fi
  ckan="$(lc_ckan_dir)"
  if [[ -n "$ckan" ]]; then
    (cd "$ckan" && "${lc_compose[@]}" stop >/dev/null 2>&1) && ok "Stopped its CKAN ($ckan)."
  fi
  return 0
}

lc_start() {
  local ids ckan port
  ids="$(lc_containers -a | tr '\n' ' ' | sed 's/ *$//')"
  [[ -n "$ids" ]] || fail "Endpoint '$lc_instance' has no containers (Compose project $lc_project); run the installer to create them."
  ckan="$(lc_ckan_dir)"
  if [[ -n "$ckan" ]]; then
    (cd "$ckan" && "${lc_compose[@]}" start >/dev/null 2>&1) && ok "Started its CKAN ($ckan)."
  fi
  # Started as they were created, on the ports they were created with. A
  # "docker compose up" by hand would publish the default port instead (#370).
  # shellcheck disable=SC2086
  docker start $ids >/dev/null
  port="$(lc_port)"
  ok "Started Endpoint '$lc_instance'${port:+ on port $port}."
}

lc_uninstall() {
  local ids volumes networks ckan reply
  info "This removes Endpoint '$lc_instance' (Compose project $lc_project): its containers,"
  info "its networks and the .env backups, which hold old credentials."
  if [[ "$remove_data" == "true" ]]; then
    warn "--remove-data: its volumes -- the catalog, the files in MinIO, everything it stored --"
    warn "and its .env and install state are deleted too. This cannot be undone."
  else
    info "Its data, .env and install state are kept (--remove-data deletes them)."
  fi
  if [[ "$assume_yes" != "true" ]]; then
    [[ -t 0 ]] || fail "uninstall asks for confirmation; run it with --yes where nobody can answer."
    read -r -p "Remove it? [y/N] " reply
    [[ "$reply" =~ ^[Yy]$ ]] || fail "Aborted; nothing was changed."
  fi

  ids="$(lc_containers -a | tr '\n' ' ' | sed 's/ *$//')"
  # shellcheck disable=SC2086
  [[ -z "$ids" ]] || docker rm -f $ids >/dev/null
  networks="$(docker network ls -q --filter "label=com.docker.compose.project=$lc_project" 2>/dev/null | tr '\n' ' ' | sed 's/ *$//' || true)"
  # shellcheck disable=SC2086
  [[ -z "$networks" ]] || docker network rm $networks >/dev/null 2>&1 || true
  ok "Removed its containers and networks."

  ckan="$(lc_ckan_dir)"
  if [[ -n "$ckan" && "$(lc_state CKAN_CREATED)" == "yes" ]]; then
    if [[ "$remove_data" == "true" ]]; then
      (cd "$ckan" && "${lc_compose[@]}" down -v >/dev/null 2>&1) || true
      ok "Removed the CKAN installed for it, with its data; its files remain: rm -rf $ckan"
    else
      (cd "$ckan" && "${lc_compose[@]}" down >/dev/null 2>&1) || true
      ok "Removed the CKAN containers installed for it; its data is kept, files at $ckan"
    fi
  elif [[ -n "$ckan" ]]; then
    info "The CKAN at $ckan was not created by this installer; left as it is."
  fi

  rm -f "$REPO_ROOT"/.env.backup.*
  ok "Removed the .env backups."

  if [[ "$remove_data" == "true" ]]; then
    volumes="$(docker volume ls -q --filter "label=com.docker.compose.project=$lc_project" 2>/dev/null | tr '\n' ' ' | sed 's/ *$//' || true)"
    # shellcheck disable=SC2086
    [[ -z "$volumes" ]] || docker volume rm $volumes >/dev/null
    rm -f "$REPO_ROOT/.env" "$REPO_ROOT/.env.install-state"
    ok "Removed its data volumes, .env and install state."
  else
    ok "Data volumes, .env and install state kept; the installer reuses them."
  fi

  if [[ "$(lc_state NETBIRD)" == "yes" || "$remove_data" == "true" ]] && command -v netbird >/dev/null 2>&1; then
    info "This machine stays in NDP's NetBird network, which other Endpoints on it may use."
    info "To leave it: sudo netbird down (and sudo netbird service uninstall to remove the client)."
  fi
  info "The checkout is left at $REPO_ROOT; remove it when no longer needed."
}

if [[ -z "$subcommand" && "$remove_data" == "true" ]]; then
  fail "--remove-data only goes with uninstall."
fi

if [[ -n "$subcommand" ]]; then
  command -v docker >/dev/null 2>&1 || fail "docker is required."
  if docker compose version >/dev/null 2>&1; then
    lc_compose=(docker compose)
  else
    lc_compose=(docker-compose)
  fi
  lc_instance="$instance"
  [[ -n "$lc_instance" ]] || lc_instance="$(lc_state EP_INSTANCE)"
  [[ -n "$lc_instance" ]] || lc_instance="ndp"
  lc_project="$(lc_project)"
  case "$subcommand" in
    status)    lc_status ;;
    stop)      lc_stop ;;
    start)     lc_start ;;
    uninstall) lc_uninstall ;;
  esac
  exit 0
fi

banner

# Which Federation this run will talk to, before anything happens. The script
# this installer replaces printed it, and with --env selecting the URL by name
# it is no longer evident from the command line (issue #285).
info "Federation: $federation_url"

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
# A time limit on building and starting (issue #376)
# --------------------------------------------------------------
# "docker compose up --build" pulls and builds, and a pull stalled on a
# registry, a rate limit or a proxy never returns: the run used to wait for
# ever, with every earlier step reported as done. It now gives up after
# --compose-timeout and says what to check; a heartbeat every minute tells a
# slow first build from a hang.
if [[ "$compose_timeout" == "0" || "$compose_timeout" == "0s" ]]; then
  compose_limit=""
  info "Docker Compose time limit: none"
elif ! command -v timeout >/dev/null 2>&1; then
  compose_limit=""
  warn "'timeout' is not installed, so building and starting have no time limit."
elif [[ "$compose_timeout" == *s ]]; then
  compose_limit="$compose_timeout"
  info "Docker Compose time limit: ${compose_timeout}"
else
  compose_limit="$((compose_timeout * 60))s"
  info "Docker Compose time limit: ${compose_timeout} min"
fi

# compose_up WHAT DIR COMMAND... -- runs COMMAND in DIR within the limit.
# Returns its status; 124 means the limit ran out.
compose_up() {
  local what="$1" dir="$2"; shift 2
  local started=$SECONDS rc=0 beat
  # The sleep is waited on rather than run in the foreground so that stopping
  # the heartbeat stops it too: left behind, it would hold the terminal (and
  # the install log's pipe) open for up to a minute after the run ended.
  (
    nap=""
    trap 'kill "$nap" 2>/dev/null; exit 0' TERM
    while :; do
      sleep 60 & nap=$!
      wait "$nap"
      info "Still building and starting $what ($(( (SECONDS - started) / 60 )) min so far)"
    done
  ) &
  beat=$!
  if [[ -n "$compose_limit" ]]; then
    (cd "$dir" && timeout -k 30 "$compose_limit" "$@") || rc=$?
  else
    (cd "$dir" && "$@") || rc=$?
  fi
  kill "$beat" 2>/dev/null || true
  wait "$beat" 2>/dev/null || true
  return "$rc"
}

compose_stalled() {
  local what="$1" dir="$2"
  fail "Building and starting $what did not finish within ${compose_limit}.
       A pull or build is probably stalled. Check that this machine reaches the
       registry (try: docker pull python:3.13-slim), Docker Hub's rate limit
       (docker login helps), and any proxy; then run the installer again, which
       picks up where it stopped. A slow machine can allow more time with
       --compose-timeout <minutes>. To look: cd $dir && ${COMPOSE[*]} logs"
}

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

# The probe opens descriptor 3 inside the subshell, which closes it on exit.
# There is nothing to close afterwards: a follow-up "exec 3>&- 2>/dev/null"
# used to sit here and in the two other probes, and its only lasting effect
# was to send stderr to /dev/null for the rest of the run, so every later
# warn and fail went unseen (issue #313).
port_free() {
  if (exec 3<>"/dev/tcp/127.0.0.1/$1") 2>/dev/null; then
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
# A checkout with neither file has never been installed. New installations
# join NetBird by default; one installed earlier keeps what it had (#363).
fresh_install="false"
[[ -f "$STATE_FILE" || -f "$REPO_ROOT/.env" ]] || fresh_install="true"

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

# The instance this checkout runs as (issue #355). Remembered in the install
# state, so re-running the installer -- the way an Endpoint is upgraded --
# keeps it without --instance.
saved_instance="$(state_get EP_INSTANCE)"
[[ -n "$instance" ]] || instance="${saved_instance:-ndp}"
[[ "$instance" =~ ^[a-z][a-z0-9-]{0,30}$ ]] \
  || fail "--instance must start with a letter and hold only lowercase letters, digits and '-' (got: $instance)"
# A checkout keeps the instance it was installed as. Renaming it would start a
# new Compose project: new containers and new, empty volumes, with the data
# left behind in the old ones.
if [[ -f "$REPO_ROOT/.env" && "$instance" != "${saved_instance:-ndp}" ]]; then
  fail "This checkout already runs the Endpoint '${saved_instance:-ndp}'; it cannot become '$instance'.
       Install another Endpoint from its own checkout (from the web: EP_INSTALL_DIR,
       default ~/ndp-ep-$instance)."
fi

# A port for a named instance: the one remembered for it, else the first free
# one from DEFAULT that this run has not handed out already. Sets $picked (not
# echoed: a subshell would lose the ports handed out). Kept in the install
# state, because a re-run finds its own ports taken and must not move them.
taken_ports=" "
pick_port() {
  # pick_port VARIABLE DEFAULT
  picked="$(state_get "$1")"
  if [[ -z "$picked" ]]; then
    picked="$2"
    while ! port_free "$picked" || [[ "$taken_ports" == *" $picked "* ]] \
      || [[ "$picked" == "$ep_api_port" ]]; do
      picked=$((picked + 1))
    done
  fi
  taken_ports+="$picked "
  [[ "$dry_run" == "true" ]] || state_set "$1" "$picked"
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

with_scheme() {
  # Prepend https:// when a URL is given without one. The Federation validates
  # jupyter_url as a full URL, so a bare host like 'jupyter.example.org' would
  # otherwise be rejected and take the whole registration down with it.
  local url="$1"
  [[ -z "$url" || "$url" == *://* ]] && { printf '%s' "$url"; return; }
  printf 'https://%s' "$url"
}

# --------------------------------------------------------------
# Collect the values that will override the documented defaults.
# --------------------------------------------------------------
overrides_file="$(mktemp)"
trap 'rm -f "$overrides_file" "${config_file:-}"; finish_log' EXIT
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
# Credentials of the bundled MongoDB and MinIO (issue #375)
# --------------------------------------------------------------
# They were the same demo pairs on every Endpoint (admin/admin123,
# minioadmin/minioadmin123), and a named instance publishes both services on
# host ports. A new installation now generates its own and keeps them in the
# install state. One whose service already holds data keeps what it was
# created with -- from the install state, the current .env, or, with neither,
# the demo pair when a data volume is already there -- since MongoDB and MinIO
# only accept the credentials their data was created with.
current_env() {
  # current_env KEY -- the value in the .env this run is about to replace.
  [[ -f "$REPO_ROOT/.env" ]] || return 0
  grep -E "^$1=" "$REPO_ROOT/.env" | tail -n1 | cut -d= -f2- | sed 's/^"\(.*\)"$/\1/' || true
}

compose_volume_exists() {
  # The project is ndp-ep-<instance> for a named instance, otherwise Compose's
  # default: the checkout's directory name.
  local project
  if [[ "$instance" != "ndp" ]]; then
    project="ndp-ep-$instance"
  else
    project="$(basename "$REPO_ROOT" | tr '[:upper:]' '[:lower:]' | tr -cd 'a-z0-9_-')"
  fi
  docker volume inspect "${project}_$1" >/dev/null 2>&1
}

new_secret() { python3 -c 'import secrets; print(secrets.token_urlsafe(24))'; }

bundled_mongodb_password() {
  local password
  password="$(state_get MONGODB_ROOT_PASSWORD)"
  if [[ -z "$password" ]]; then
    password="$(current_env MONGODB_CONNECTION_STRING | sed -n 's|^mongodb://admin:\([^@]*\)@mongodb:27017.*|\1|p')"
  fi
  if [[ -z "$password" ]] && compose_volume_exists mongodb_data; then
    password="admin123"
  fi
  [[ -n "$password" ]] || password="$(new_secret)"
  if [[ "$password" == "admin123" ]]; then
    warn "The bundled MongoDB keeps the demo password it was created with (admin123);
       its data only opens with it. See docs/operations.md to change it."
  fi
  [[ "$dry_run" == "true" ]] || state_set MONGODB_ROOT_PASSWORD "$password"
  put MONGODB_ROOT_PASSWORD "$password"
  put MONGODB_CONNECTION_STRING "mongodb://admin:${password}@mongodb:27017"
}

bundled_minio_keys() {
  local access secret
  access="$(state_get MINIO_ROOT_USER)"; secret="$(state_get MINIO_ROOT_PASSWORD)"
  if [[ -z "$access" || -z "$secret" ]] && [[ "$(current_env S3_ENDPOINT)" == "minio:9000" ]]; then
    access="$(current_env S3_ACCESS_KEY)"; secret="$(current_env S3_SECRET_KEY)"
  fi
  if [[ -z "$access" || -z "$secret" ]] && compose_volume_exists minio_data; then
    access="minioadmin"; secret="minioadmin123"
  fi
  if [[ -z "$access" || -z "$secret" ]]; then
    access="ndp-$(python3 -c 'import secrets; print(secrets.token_hex(4))')"
    secret="$(new_secret)"
  fi
  if [[ "$secret" == "minioadmin123" ]]; then
    warn "The bundled MinIO keeps the demo keys it was created with (minioadmin)."
  fi
  if [[ "$dry_run" != "true" ]]; then
    state_set MINIO_ROOT_USER "$access"
    state_set MINIO_ROOT_PASSWORD "$secret"
  fi
  put S3_ACCESS_KEY "$access"
  put S3_SECRET_KEY "$secret"
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
    "Your personal NDP access token. Get it from the user section of" \
    "https://nationaldataplatform.org/ (sign in, then open your user panel)." \
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
    "Federation; if the name is already taken you will be asked for another."
  ask ep_name "Endpoint name" "${ep_name:-my_endpoint}"

  section "Contact email" \
    "The point of contact recorded for this Endpoint, for administrators to" \
    "reach whoever runs it."
  ask poc "Contact email" ""
  [[ -n "$poc" ]] || fail "A contact email is required to register."

  # The Federation requires ckan_name/ckan_password fields but only stores
  # them — it never authenticates or provisions with them (the staging-catalog
  # token is fetched with the user's own bearer token), and this installer
  # never reads them back from a fetched config. So they are sent empty rather
  # than prompted for: an Endpoint on MongoDB has no catalog admin, and one on
  # CKAN gets its sysadmin from the CKAN install step. Sending them empty also
  # keeps a real password out of the Federation's unauthenticated /ep/{id}.
  ckan_user=""
  ckan_pass=""

  section "Listed on the platform" \
    "Whether this Endpoint reports its status to the NDP, so it shows up as" \
    "an active, discoverable Endpoint on the platform. This is about" \
    "visibility only — it does NOT control who can read this Endpoint's" \
    "data; that is governed by its access groups and roles."
  ask_yes_no public_ep "List this Endpoint on the platform?" "yes"

  echo
  echo "${BLUE}The rest are optional features, off by default. Each can be"
  echo "  changed later; leave them off if unsure.${NC}"

  # enable_staging is a required registration field but left off for now, so it
  # is sent as false rather than prompted for.
  staging="no"

  local jupyter_url=""
  section "JupyterHub" \
    "Show a JupyterHub link in the Endpoint's UI, for users to open notebooks" \
    "against this Endpoint's data."
  ask_yes_no jhub "Enable JupyterHub?" "no"
  if [[ "$jhub" == "yes" ]]; then
    ask jupyter_url "JupyterHub URL the link should point to" ""
    jupyter_url="$(with_scheme "$jupyter_url")"
    [[ -n "$jupyter_url" ]] || { warn "No URL given; JupyterHub left off."; jhub="no"; }
  fi

  section "Data streaming" \
    "Let this Endpoint manage and stream Kafka topics, for real-time data" \
    "rather than static datasets. Needs a reachable Kafka broker."
  ask_yes_no streaming "Enable data streaming (Kafka)?" "no"

  section "Remote execution" \
    "Let this Endpoint drive the Remote Execution Deployment API, to launch" \
    "compute jobs. Needs that service configured."
  ask_yes_no rexec "Enable remote execution?" "no"
  if [[ "$rexec" == "yes" ]]; then
    ask reg_rexec_url "Remote Execution Deployment API URL" ""
    reg_rexec_url="$(with_scheme "$reg_rexec_url")"
    [[ -n "$reg_rexec_url" ]] || { warn "No URL given; remote execution left off."; rexec="no"; }
  fi

  local proceed confirmed="no"
  # Confirm once before creating anything; a name clash then loops back to ask
  # for a different name without re-confirming the rest.
  while true; do
    if [[ "$confirmed" != "yes" ]]; then
      echo
      echo "  About to register '${ep_name}' for '${organization}' at ${federation_url%/}."
      ask_yes_no proceed "Continue?" "yes"
      [[ "$proceed" == "yes" ]] || fail "Aborted; nothing was registered."
      confirmed="yes"
    fi

    # Values are passed through the environment and typed in Python, so a
    # name containing quotes or spaces cannot break the JSON, and booleans are
    # real booleans (an earlier version substituted bash `true`/`false`
    # straight into Python source, which is not valid there).
    local payload
    payload="$(
      REG_CKAN_USER="$ckan_user" REG_CKAN_PASS="$ckan_pass" \
      REG_POC="$poc" REG_ORG="$organization" REG_EP_NAME="$ep_name" \
      REG_USERID="$userid" \
      REG_STAGING="$staging" REG_JHUB="$jhub" REG_STREAMING="$streaming" \
      REG_REXEC="$rexec" REG_PUBLIC="$public_ep" REG_JUPYTER_URL="$jupyter_url" \
      python3 <<'PY'
import json, os


def flag(name):
    return os.environ.get(name) == "yes"


payload = {
    "ckan_name": os.environ["REG_CKAN_USER"],
    "ckan_password": os.environ["REG_CKAN_PASS"],
    "enable_staging": flag("REG_STAGING"),
    "poc": os.environ["REG_POC"],
    "organization": os.environ["REG_ORG"],
    "jhub": flag("REG_JHUB"),
    "streaming": flag("REG_STREAMING"),
    "rexec": flag("REG_REXEC"),
    "ep_name": os.environ["REG_EP_NAME"],
    "userid": os.environ["REG_USERID"],
    "public": flag("REG_PUBLIC"),
}
# Optional: the Federation stores it and returns it, and the installer reads it
# back into JUPYTER_URL. Only sent when JupyterHub is on and a URL was given.
if flag("REG_JHUB") and os.environ.get("REG_JUPYTER_URL"):
    payload["jupyter_url"] = os.environ["REG_JUPYTER_URL"]
print(json.dumps(payload))
PY
)"

    response="$(mktemp)"
    http_code="$(curl -s -o "$response" -w '%{http_code}' -m 60 \
      -X POST "${federation_url%/}/ep/simple" \
      -H "Authorization: Bearer $token" \
      -H "Content-Type: application/json" \
      -d "$payload" || echo 000)"

    body="$(cat "$response")"
    rm -f "$response"

    if [[ "$http_code" == "400" ]] && interactive; then
      # The most common 400 is a name already taken. Rather than abort and
      # lose everything typed so far, ask for a different name and retry.
      warn "The Federation rejected the name '${ep_name}': ${body}"
      warn "This usually means an Endpoint with that name already exists."
      local taken="$ep_name"
      # No default here, so pressing Enter cannot resubmit the same name.
      while true; do
        ask ep_name "Try a different Endpoint name" ""
        [[ -n "$ep_name" && "$ep_name" != "$taken" ]] && break
        ep_name="$taken"
        warn "Please enter a name different from '${taken}'."
      done
      continue
    fi

    # Pull the human-readable reason out of the JSON body, falling back to the
    # raw body when it is not the shape we expect.
    local reason
    reason="$(python3 - "$body" <<'PY'
import json, sys
try:
    d = json.loads(sys.argv[1])
    print(d.get("message") or d.get("detail") or d.get("error") or sys.argv[1])
except Exception:
    print(sys.argv[1])
PY
)"

    case "$http_code" in
      201) break ;;
      000)
        fail "Could not reach the Federation at ${federation_url%/}.
       Check the URL and your network, then try again."
        ;;
      400)
        fail "The Federation rejected the registration:
         ${reason}
       An Endpoint with this name may already exist."
        ;;
      401)
        fail "The Federation did not accept your access token.
       It may have expired — get a fresh one from your user section at
       https://nationaldataplatform.org/ and run the installer again."
        ;;
      422)
        fail "The Federation rejected some of the values:
         ${reason}
       If you gave a JupyterHub URL, it must be a full URL (the installer
       adds https:// when the scheme is missing) and the email a valid one."
        ;;
      502|503|504)
        # The Federation reached a downstream service (Affinities, Keycloak,
        # CKAN) that is down. This is not the operator's fault, and the
        # Federation does not roll back, so a partial registration may exist.
        local service="a required service"
        case "$reason" in
          *[Aa]ffinities*) service="the Affinities service" ;;
          *[Kk]eycloak*)   service="the identity provider (Keycloak)" ;;
          *[Cc][Kk][Aa][Nn]*) service="the CKAN service" ;;
        esac
        fail "Your details were accepted, but the Federation could not finish:
       ${service} it depends on is currently unavailable (HTTP ${http_code}).

       This is NOT a problem with your token or your answers — it is a
       temporary outage on the platform side. Reported reason:
         ${reason}

       The Federation may have partially registered '${ep_name}' before
       failing, so retrying with the same name could report that it already
       exists. When the service is back, register again with a different
       Endpoint name, or ask the platform administrator to clear the partial
       registration for '${ep_name}'."
        ;;
      *)
        fail "The Federation answered HTTP ${http_code}:
         ${reason}"
        ;;
    esac
  done

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
  echo
  info "Keep this id — re-running the installer with --config-id $config_id"
  info "reproduces this Endpoint without registering again."
}

# --------------------------------------------------------------
# Settings the Federation remembers for this Endpoint
# --------------------------------------------------------------
# A Federation configuration records eleven things. The rest of what an
# Endpoint runs with has lived only in the local .env.install-state, so
# reinstalling on another machine meant answering from memory. These two
# halves put the answers under the configuration id instead (issue #287).
#
# The token is this operator's own NDP access token, the same one registering
# uses. It is asked for only when they accept, because in this flow the
# registration happened in the browser and the installer never sees one.
remember_token=""

offer_remembered_settings() {
  local answer stored

  section "Remembered settings" \
    "Your Federation configuration can also hold the answers below, so" \
    "installing this Endpoint again — here or on another machine — reuses" \
    "them instead of asking you to remember." \
    "" \
    "This needs your NDP access token, from the user section of the" \
    "platform. Say no and nothing is sent anywhere; the answers are still" \
    "kept on this machine for the next run."
  ask_yes_no answer "Use your Federation configuration to remember these?" "yes"

  [[ "$answer" == "yes" ]] || return 0

  ask_secret remember_token "Your NDP access token (not shown)"
  if [[ -z "$remember_token" ]]; then
    warn "No token given — the answers will only be kept on this machine."
    return 0
  fi

  stored="$(fetch_remembered_settings)" || {
    warn "Could not read the remembered settings. Carrying on without them."
    remember_token=""
    return 0
  }

  apply_remembered_settings "$stored"
}

fetch_remembered_settings() {
  local http_code body
  body="$(curl -s -m 20 -w $'\n%{http_code}' \
    -H "Authorization: Bearer $remember_token" \
    "${federation_url%/}/ep/${config_id}/settings" 2>/dev/null || true)"

  http_code="${body##*$'\n'}"
  body="${body%$'\n'*}"

  case "$http_code" in
    200) echo "$body"; return 0 ;;
    401) warn "The Federation did not accept that access token." ;;
    403) warn "That token does not own configuration ${config_id}." ;;
    404) echo "{}"; return 0 ;;
    *)   warn "The Federation answered HTTP ${http_code:-000} for the remembered settings." ;;
  esac

  return 1
}

apply_remembered_settings() {
  # Only the answers this installer knows are taken back; see
  # install/remembered_settings.py for which, and why credentials are not
  # among them.
  local assignments
  assignments="$(python3 "$REPO_ROOT/install/remembered_settings.py" load "$1")"

  # Reported by what came back, not by the request having been made. A
  # Federation old enough to lack the settings routes answers 404, which is
  # nothing to load rather than a failure -- but saying "loaded" there told
  # every operator their settings had been restored when none existed and
  # none could (issue #289).
  if [[ -z "$assignments" ]]; then
    info "Nothing is remembered for this Endpoint yet."
    return 0
  fi

  eval "$assignments"
  ok "Loaded the settings remembered for this Endpoint."
}

save_remembered_settings() {
  [[ -n "$remember_token" && -n "$config_id" ]] || return 0

  local payload http_code
  payload="$(python3 "$REPO_ROOT/install/remembered_settings.py" save \
    "backend=$backend" \
    "want_s3=$want_s3" \
    "s3_endpoint=$s3_endpoint" \
    "s3_secure=$s3_secure" \
    "ep_api_port=$ep_api_port" \
    "auth_api_url=$auth_api_url" \
    "want_access_requests=$want_access_requests" \
    "mongodb_url=$mongodb_url" \
    "ckan_url=$ckan_url")"

  http_code="$(curl -s -o /dev/null -w '%{http_code}' -m 20 \
    -X PUT "${federation_url%/}/ep/${config_id}/settings" \
    -H "Authorization: Bearer $remember_token" \
    -H "Content-Type: application/json" \
    -d "$payload" 2>/dev/null || echo 000)"

  case "$http_code" in
    200) ok "Saved these answers to configuration ${config_id}." ;;
    404) warn "This Federation does not offer remembered settings yet. Nothing was saved." ;;
    *)   warn "Could not save the answers (HTTP ${http_code}). The install is unaffected." ;;
  esac
}


# --------------------------------------------------------------
# Ask, when there is nobody to ask but the person running this.
# --------------------------------------------------------------
# A Federation registration answers most of these. Without one, and on a
# terminal, ask rather than silently installing a demo nobody asked for.
organization=""
ep_name=""
auth_api_url=""

# Asked whether or not there is a configuration id. A registration answers
# eleven things; none of them is the catalog, object storage, access requests
# or the ports. Gating the whole block on not having a configuration id meant
# the platform's flow -- which passes one and nothing else, and is the flow
# almost every Endpoint is installed through -- asked nothing and took every
# default, LOCAL_CATALOG_BACKEND=none among them (issue #287). The questions
# that only make sense without a configuration id are guarded individually.
if interactive; then
  echo
  echo "  A few questions, then nothing is written until you confirm."
  echo "  Press Enter to accept the value in brackets."

  if [[ -z "$config_id" ]]; then
  section "Configuration id" \
    "Identifies this Endpoint's registration in the NDP Federation, the" \
    "central registry of all Endpoints. The registration holds the settings" \
    "the Endpoint runs with (organization, access group, catalog, identity" \
    "provider) and is what lists it on the platform." \
    "" \
    "Paste it if you already registered (on the platform or a previous run)." \
    "Leave blank and the next step offers to register now."
  ask config_id "Configuration id (blank to skip)" ""
  fi

  # With a configuration id in hand, offer to use the Federation as the memory
  # for everything it does not itself record. Opt-in on purpose: declining
  # asks for no token and leaves the run exactly as it was before.
  if [[ -n "$config_id" ]]; then
    offer_remembered_settings
  fi

  # Catalog first, so the reason the later CKAN questions (ports, sysadmin)
  # appear is already established, and the registration does not ask about a
  # catalog before you have said which one you want.
  section "Local catalog" \
    "Choose what this Endpoint uses as its local data catalog — where the" \
    "datasets published to it are stored." \
    "" \
    "With no local catalog nothing is installed or stored here: the Endpoint" \
    "authenticates users, searches the platform's global catalog and is" \
    "listed in the Federation. It is the quickest one to stand up, and a" \
    "catalog can be added later by running this again."
  choose backend_choice "Which local catalog should this Endpoint use?" 1 \
    "None — nothing is stored locally (quickest)" \
    "MongoDB, installed alongside the Endpoint" \
    "MongoDB, one I already have" \
    "CKAN, installed by this script (takes several minutes)" \
    "CKAN, one I already have"
  case "$backend_choice" in
    1) backend="none"; mongodb_url=""; ckan_url="" ;;
    2) backend="mongodb"; mongodb_url="" ;;
    3) backend="mongodb"
       section "Existing MongoDB" \
         "Connect to a MongoDB you already run, instead of installing one." \
         "Give its connection string, reachable from the Endpoint container."
       ask mongodb_url "MongoDB connection string" \
         "mongodb://host.docker.internal:27017"
       ;;
    4) backend="ckan"; ckan_url="" ;;
    5) backend="ckan"
       section "Existing CKAN" \
         "Connect to a CKAN you already run. The key is verified before" \
         "anything is written."
       ask ckan_url       "CKAN URL" ""
       ask_secret ckan_api_key "CKAN API key (not shown)"
       ask ckan_sysadmin  "CKAN username that key belongs to (blank to skip verifying it)" ""
       ;;
  esac

  section "S3 object storage" \
    "Object storage for buckets and files, managed from the Endpoint's UI." \
    "" \
    "Install MinIO alongside the Endpoint, or point at an S3-compatible" \
    "service you already run (including Amazon S3). Leave it off and the S3" \
    "tools are simply absent."
  ask_yes_no want_s3 "Enable S3 object storage?" "no"
  if [[ "$want_s3" == "yes" ]]; then
    choose s3_choice "Which S3 should this Endpoint use?" 1 \
      "MinIO, installed alongside the Endpoint" \
      "An S3-compatible service I already have"
    # The bundled MinIO drops an endpoint remembered from a run that used an
    # existing S3; left set, it sent the run down the existing-S3 path with no
    # keys, which stops the install (issue #345).
    [[ "$s3_choice" == "1" ]] && s3_endpoint=""
    if [[ "$s3_choice" == "2" ]]; then
      section "Existing S3" \
        "Connect to an S3-compatible service you already run. Give the" \
        "endpoint, credentials and region, reachable from the Endpoint" \
        "container."
      ask s3_endpoint "S3 endpoint (host:port, or s3.amazonaws.com)" ""
      ask s3_access_key "S3 access key" ""
      ask_secret s3_secret_key "S3 secret key (not shown)"
      ask s3_region "S3 region" "us-east-1"
      ask_yes_no s3_secure "Use https to reach it?" "no"
      s3_secure="$( [[ "$s3_secure" == "yes" ]] && echo True || echo False )"
      [[ -n "$s3_endpoint" ]] || { warn "No endpoint given; S3 left off."; want_s3="no"; }
    fi
  fi

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
    ckan_ports_given="true"
    ask ckan_sysadmin  "CKAN sysadmin to create" "ckan_admin"
  fi

  section "Authentication service" \
    "The AAI endpoint the Endpoint validates login tokens against. Keep the" \
    "default to authenticate against the National Data Platform."
  ask auth_api_url "Authentication service (AAI) URL" \
    "https://idp.nationaldataplatform.org/temp/information"

  section "Access requests" \
    "A self-service workflow: someone without access to this Endpoint asks" \
    "for it from the login screen, and an administrator approves or rejects" \
    "it from the UI. Without this, access is arranged outside the Endpoint." \
    "" \
    "The requests are stored in MongoDB, whatever the catalog is. One is" \
    "installed for it unless the catalog already provides one."
  ask_yes_no want_access_requests "Enable access requests?" "no"

  # Last, so it stores what was actually answered rather than what was
  # offered. A failure here warns and nothing else: the Endpoint installs
  # the same whether or not the Federation accepted the answers.
  save_remembered_settings

fi

# example.env is written as a demo that shows every setting, so its defaults
# have the optional integrations switched on. Inheriting those would produce an
# Endpoint pointing at Kafka, MinIO, JupyterLab and Pelican that nothing has
# provisioned. Everything optional starts off here, and is switched back on
# further down only when something actually provides it.
# IS_PUBLIC is what allows the metrics task to post to the Federation. An
# Endpoint that never registered has no business reporting to a platform it is
# not part of, and example.env's demo default of True made it do exactly that.
# A registration decides it further down, from the answer given while
# registering; without one it stays off.
put IS_PUBLIC "False"
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
# Platform URLs the Federation serves with each configuration (1.12.9) and the
# id Affinities gave this Endpoint when it registered (issue #359).
emit("fed_netbird_url", cfg.get("netbird_management_url") or "")
emit("fed_affinities_url", cfg.get("affinities_url") or "")
emit("fed_affinities_uid", cfg.get("affinities_uid") or "")
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

  # Remote execution: the Federation stores no URL for it, so it is applied
  # from what registration captured. Enabled only when a URL is present, since
  # REXEC_CONNECTION without REXEC_DEPLOYMENT_API_URL has nothing to talk to.
  if [[ -n "$reg_rexec_url" ]]; then
    put REXEC_CONNECTION "True"
    put REXEC_DEPLOYMENT_API_URL "$reg_rexec_url"
  fi

  if [[ -n "$fed_pre_ckan_url" && -n "$fed_pre_ckan_key" ]]; then
    put PRE_CKAN_ENABLED "True"
    put PRE_CKAN_URL "$fed_pre_ckan_url"
    put PRE_CKAN_API_KEY "$fed_pre_ckan_key"
    # Without this, a promoted dataset keeps the organization it has locally —
    # 'services', or whatever the local catalog calls it — and the staging
    # credentials cannot write there, so every publish fails with an
    # authorization error naming a user rather than the missing setting. The
    # organization the token can write to is the one the Federation minted it
    # for, which is this Endpoint's configuration id.
    put PRE_CKAN_ORGANIZATION "ep-${config_id}"
  else
    put PRE_CKAN_ENABLED "False"
  fi

  put IS_PUBLIC "$([[ "$fed_public" == "true" ]] && echo True || echo False)"

  # The client the registration creates is confidential and its tokens carry no
  # `sub`, which AUTH_API_URL looks the user up by — so it cannot be used for
  # sign-in as it stands. The installer says it exists and stops there; see
  # docs/configuration.md.
  if [[ -n "$fed_client_id" ]]; then
    info "Registration includes client id '$fed_client_id' for realm '$fed_realm'."
  fi
elif [[ "${already_warned:-false}" != "true" ]]; then
  warn "No --config-id given: installing without a Federation registration."
  warn "The Endpoint will not be listed in the Federation."
fi

# Metrics go to the Federation this run was pointed at. Left to example.env,
# METRICS_ENDPOINT stayed on production whatever --env or --federation-url
# said, so an Endpoint registered with the test Federation reported to
# production instead and was never seen as alive where it was registered
# (issue #307). Written unconditionally: without a registration IS_PUBLIC is
# False and nothing is posted, but the setting still names the right place.
put METRICS_ENDPOINT "${federation_url%/}/metrics/"

# --------------------------------------------------------------
# Affinities and NetBird (issue #359)
# --------------------------------------------------------------
# Remembered: a re-run keeps what the last run of this checkout turned on, so
# an upgrade does not quietly switch them off. Affinities is opt-in. NetBird is
# on by default for a new installation (issue #363) and then must never stop
# it: "default" joins when it can and otherwise says why and carries on, and a
# failed default join is tried again on the next run. --netbird, or a join
# that succeeded, makes it required. An Endpoint installed before, with
# nothing recorded, only joins with --netbird.
[[ -n "$want_affinities" ]] || want_affinities="$(state_get AFFINITIES)"
[[ -n "$want_netbird" ]]    || want_netbird="$(state_get NETBIRD)"
if [[ -z "$want_netbird" && "$fresh_install" == "true" ]]; then
  want_netbird="default"
fi

if [[ "$want_affinities" == "yes" ]]; then
  # The Federation registers each Endpoint in Affinities and keeps the id it
  # got back; it also says where Affinities is. Both come with the
  # configuration, so there is nothing to type and nothing fixed here.
  [[ -n "${fed_affinities_url:-}" && -n "${fed_affinities_uid:-}" ]] \
    || fail "--affinities needs a Federation registration that names the Affinities service and this Endpoint's Affinities id.
       Federation configuration: ${fed_affinities_url:-no Affinities URL} / ${fed_affinities_uid:-no Affinities id}.
       The URL comes with Federation 1.12.9 or later; the id is set when the
       Endpoint registers while the Federation has AFFINITIES_API_URL."
  put AFFINITIES_ENABLED "True"
  put AFFINITIES_URL "$fed_affinities_url"
  put AFFINITIES_EP_UUID "$fed_affinities_uid"
  ok "Affinities integration on ($fed_affinities_url, id $fed_affinities_uid)"
  [[ "$dry_run" == "true" ]] || state_set AFFINITIES yes
fi

netbird_status() {
  # The client's own view: management connection and address, as JSON. Read
  # as the user first, which needs no sudo; through sudo only if that fails.
  netbird status --json 2>/dev/null \
    || { [[ ${#netbird_sudo[@]} -gt 0 ]] && "${netbird_sudo[@]}" netbird status --json 2>/dev/null; } \
    || true
}

netbird_field() {
  # netbird_field connected|ip|url — from `netbird status --json` on stdin
  python3 -c '
import json, sys
try:
    data = json.load(sys.stdin)
except ValueError:
    data = {}
management = data.get("management") or {}
print({
    "connected": "yes" if management.get("connected") else "no",
    "ip": (data.get("netbirdIp") or "").split("/")[0],
    "url": management.get("url") or "",
}[sys.argv[1]])' "$1"
}

netbird_stop() {
  # Required (--netbird): stop the installation. Default: say why NetBird was
  # not joined and how to join later, and carry on without it.
  if [[ "$want_netbird" == "yes" ]]; then
    fail "$1"
  fi
  warn "This Endpoint did not join NetBird: $1
       It is installed and works without it. To join later, re-run the installer
       with --ndp-token-file <file holding your NDP access token> (or
       --netbird-setup-key-file <path>), or with --no-netbird to stop trying."
  return 1
}

# install_netbird_client -- the pinned NetBird release in install/netbird.sha256,
# installed only once its SHA-256 matches (issue #375). It replaced piping
# NetBird's install script, unpinned and unverified, into a root shell.
# EP_NETBIRD_RELEASES_URL (a mirror) and EP_NETBIRD_BIN_DIR (where the binary
# goes) default to GitHub's releases and /usr/bin.
install_netbird_client() {
  local arch name version sum work url bin_dir
  [[ "$(uname -s)" == "Linux" ]] || { warn "The NetBird client can only be installed here on Linux."; return 1; }
  case "$(uname -m)" in
    x86_64|amd64)  arch="amd64" ;;
    aarch64|arm64) arch="arm64" ;;
    *) warn "No pinned NetBird client for $(uname -m); install it by hand and run this again."; return 1 ;;
  esac
  read -r sum name < <(grep -E "_linux_${arch}\.tar\.gz\$" "$REPO_ROOT/install/netbird.sha256")
  version="$(sed -n 's/^netbird_\([0-9.]*\)_linux_.*/\1/p' <<< "$name")"
  [[ -n "$sum" && -n "$version" ]] || { warn "install/netbird.sha256 has no entry for linux/$arch."; return 1; }
  url="${EP_NETBIRD_RELEASES_URL:-https://github.com/netbirdio/netbird/releases/download}/v${version}/${name}"
  bin_dir="${EP_NETBIRD_BIN_DIR:-/usr/bin}"
  work="$(mktemp -d)"
  info "Installing the NetBird client $version (needs sudo)."
  if ! curl -fsSL -o "$work/$name" "$url"; then
    rm -rf "$work"; warn "Could not download $url"; return 1
  fi
  if ! (cd "$work" && printf '%s  %s\n' "$sum" "$name" | sha256sum -c --status); then
    rm -rf "$work"
    warn "The NetBird client downloaded from $url does not match its pinned checksum; not installed."
    return 1
  fi
  tar -xzf "$work/$name" -C "$work" netbird \
    && "${netbird_sudo[@]}" install -m 0755 "$work/netbird" "$bin_dir/netbird" \
    && "${netbird_sudo[@]}" "$bin_dir/netbird" service install \
    && "${netbird_sudo[@]}" "$bin_dir/netbird" service start \
    || { rm -rf "$work"; warn "Could not install the NetBird client service."; return 1; }
  rm -rf "$work"
  ok "Installed the NetBird client $version (sha256 verified)."
}

join_netbird() {
  step "Joining NDP's NetBird network"
  netbird_url="${netbird_management_url:-${fed_netbird_url:-}}"
  if [[ -z "$netbird_url" ]]; then
    # Without a registration there is no network to join: say nothing then.
    [[ "$want_netbird" == "default" && -z "$config_id" ]] && {
      info "No Federation registration, so no NetBird network to join."
      return 1
    }
    netbird_stop "--netbird needs the NetBird management URL: from the Federation configuration
       (Federation 1.12.9 or later, with --config-id) or --netbird-management-url." || return 1
  fi
  netbird_sudo=()
  # A machine already connected (another Endpoint on this host joined it) needs
  # no sudo at all: seeing the connection does not (issue #367).
  already_connected="no"
  if command -v netbird >/dev/null 2>&1 \
     && [[ "$(netbird_status | netbird_field connected)" == "yes" ]]; then
    already_connected="yes"
  fi
  if [[ "$(id -u)" != "0" ]]; then
    netbird_sudo=(sudo)
    # Asked for its password only where someone can answer.
    if [[ "$want_netbird" == "default" && "$already_connected" == "no" ]] \
       && ! interactive && ! sudo -n true 2>/dev/null; then
      netbird_stop "it needs sudo, and sudo would ask for a password nobody can type here." || return 1
    fi
  fi

  if [[ "$dry_run" == "true" ]]; then
    warn "--dry-run: would join $netbird_url (installing the NetBird client if missing)."
    return 1
  fi

  # Native on the host, as on the machines already in the network: the
  # Endpoint and CKAN are reached over the host's network.
  if ! command -v netbird >/dev/null 2>&1; then
    install_netbird_client || { netbird_stop "Could not install the NetBird client." || return 1; }
  fi

  if [[ "$(netbird_status | netbird_field connected)" == "yes" ]]; then
    current_url="$(netbird_status | netbird_field url)"
    ok "Already connected to NetBird (${current_url:-management URL not reported})."
    [[ -z "$current_url" || "${current_url%/}" == "${netbird_url%/}"* ]] \
      || warn "This machine is connected to $current_url, not $netbird_url; left as it is."
  else
    key_file="$netbird_setup_key_file"
    temp_key=""
    if [[ -z "$key_file" && -n "$config_id" ]]; then
      # From the Federation (1.12.10): it hands the key only to the owner of
      # this configuration, so the person installing never needs to know it
      # (issue #361). Neither the token nor the key is written anywhere but
      # these private temporary files, removed as soon as they are used.
      token="${remember_token:-}"
      if [[ -z "$token" && -n "$ndp_token_file" ]]; then
        [[ -r "$ndp_token_file" ]] \
          || { netbird_stop "Cannot read the NDP token file: $ndp_token_file" || return 1; }
        token="$(tr -d '[:space:]' < "$ndp_token_file")"
      fi
      if [[ -z "$token" ]] && interactive; then
        if [[ "$want_netbird" == "default" ]]; then
          ask_secret token "Your NDP access token, to join NetBird (not shown; Enter to skip)"
        else
          ask_secret token "Your NDP access token, to fetch the NetBird key (not shown)"
        fi
      fi
      if [[ -n "$token" ]]; then
        headers="$(mktemp)"; enrolment="$(mktemp)"
        chmod 600 "$headers" "$enrolment"
        printf 'Authorization: Bearer %s\n' "$token" > "$headers"
        unset token
        code="$(curl -s -m 20 -o "$enrolment" -w '%{http_code}' -H @"$headers" \
          "${federation_url%/}/ep/${config_id}/netbird" || echo 000)"
        rm -f "$headers"
        if [[ "$code" == "200" ]]; then
          temp_key="$(mktemp)"
          chmod 600 "$temp_key"
          python3 - "$enrolment" "$temp_key" <<'PY'
import json, sys
with open(sys.argv[1]) as handle:
    key = (json.load(handle) or {}).get("setup_key") or ""
with open(sys.argv[2], "w") as handle:
    handle.write(key)
PY
          if [[ -s "$temp_key" ]]; then
            key_file="$temp_key"
            ok "NetBird setup key received from the Federation"
          else
            rm -f "$temp_key"
            temp_key=""
            warn "The Federation's answer held no NetBird setup key."
          fi
        else
          case "$code" in
            401) warn "The Federation did not accept that NDP token." ;;
            403) warn "That NDP token does not own configuration $config_id." ;;
            404) warn "This Federation does not hand out NetBird keys (needs 1.12.10 or later)." ;;
            503) warn "This Federation has no NetBird setup key configured." ;;
            *)   warn "The Federation answered HTTP $code for the NetBird key." ;;
          esac
        fi
        rm -f "$enrolment"
      fi
    fi
    if [[ -z "$key_file" ]]; then
      interactive || {
        netbird_stop "--netbird needs the setup key: give your NDP token (--ndp-token-file <path>) so the Federation hands it over, or pass --netbird-setup-key-file <path>." || return 1
      }
      if [[ "$want_netbird" == "default" ]]; then
        ask_secret netbird_key "NetBird setup key (not shown; Enter to skip)"
      else
        ask_secret netbird_key "NetBird setup key (not shown)"
      fi
      [[ -n "$netbird_key" ]] || { netbird_stop "No NetBird setup key given." || return 1; }
      # Through a private file, so the key is not on a command line.
      temp_key="$(mktemp)"
      chmod 600 "$temp_key"
      printf '%s' "$netbird_key" > "$temp_key"
      unset netbird_key
      key_file="$temp_key"
    fi
    [[ -r "$key_file" ]] \
      || { netbird_stop "Cannot read the NetBird setup key file: $key_file" || return 1; }
    joined="yes"
    "${netbird_sudo[@]}" netbird up --management-url "$netbird_url" \
      --setup-key-file "$key_file" || joined="no"
    [[ -n "$temp_key" ]] && rm -f "$temp_key"
    [[ "$joined" == "yes" ]] \
      || { netbird_stop "netbird up failed; see the message above." || return 1; }
    ok "Joined NetBird at $netbird_url"
  fi

  netbird_ip="$(netbird_status | netbird_field ip)"
  put NETBIRD_ENABLED "True"
  [[ -n "$netbird_ip" ]] && put NETBIRD_IP "$netbird_ip"
  ok "NetBird address ${netbird_ip:-not reported yet}, reported in the metrics"
  return 0
}

case "$want_netbird" in
  yes|default)
    if join_netbird; then
      state_set NETBIRD yes
    elif [[ "$dry_run" != "true" ]]; then
      # Only a default join gets here: try again on the next run.
      state_set NETBIRD default
    fi
    ;;
  no)
    [[ "$dry_run" == "true" ]] || state_set NETBIRD no
    ;;
esac

# --------------------------------------------------------------
step "Selecting the local catalog backend"
# --------------------------------------------------------------
# Answers given at the prompt. A Federation registration, where there is one,
# has already set organization and name, so these only fill in what it did not.
[[ -n "$organization" ]]  && put ORGANIZATION "$organization"
[[ -n "$ep_name" ]]       && put EP_NAME "$ep_name"
[[ -n "$auth_api_url" ]]  && put AUTH_API_URL "$auth_api_url"

put LOCAL_CATALOG_BACKEND "$backend"

profiles=()
# CKAN_LOCAL_ENABLED, despite the name, is the master switch for local catalog
# writes for ANY backend — it gates the registration, update, delete and
# resource routes (see api/main.py). It must be True for MongoDB too, or the
# Endpoint comes up read-only and datasets cannot be registered.
if [[ "$backend" == "none" ]]; then
  # No local catalog. Nothing is installed and nothing is stored here, so no
  # compose profile is added. CKAN_LOCAL_ENABLED must be False to match: it is
  # what leaves the routes that write to a local catalog unmounted, and with it
  # on the Endpoint would offer operations with nowhere to go. The CKAN and
  # MongoDB settings are blanked so nothing points at a service that is absent.
  put CKAN_LOCAL_ENABLED "False"
  put CKAN_URL ""
  put CKAN_API_KEY ""
  put MONGODB_CONNECTION_STRING ""
  ok "No local catalog — nothing is stored on this Endpoint"
  info "It authenticates users, searches the global catalog and reports to the Federation."
  info "Run this again with --backend mongodb or --backend ckan to add one later."
elif [[ "$backend" == "mongodb" && -n "$mongodb_url" ]]; then
  # Pointing at a MongoDB that already exists — do not start the bundled one.
  put CKAN_LOCAL_ENABLED "True"
  put MONGODB_CONNECTION_STRING "$mongodb_url"
  ok "Using the existing MongoDB at $mongodb_url"
elif [[ "$backend" == "mongodb" ]]; then
  # Provisioned by this repository's own compose file. That MongoDB is started
  # with root credentials, so the connection string must carry them — without
  # them the Endpoint cannot create indexes or write, and /search fails with
  # "Command createIndexes requires authentication".
  profiles+=("mongodb")
  put CKAN_LOCAL_ENABLED "True"
  bundled_mongodb_password
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

  # A named instance installs a CKAN of its own, next to its checkout and on
  # ports of its own. Sharing the default folder reconfigured and restarted
  # the first Endpoint's CKAN instead (issue #357).
  if [[ "$instance" != "ndp" ]]; then
    [[ -n "$ckan_dir" ]] || ckan_dir="$(dirname "$REPO_ROOT")/ndp-ckan-$instance"
    if [[ "$ckan_ports_given" != "true" ]]; then
      pick_port CKAN_SSL_PORT "$ckan_ssl_port";   ckan_ssl_port="$picked"
      pick_port CKAN_HTTP_PORT "$ckan_http_port"; ckan_http_port="$picked"
      pick_port CKAN_APP_PORT "$ckan_app_port";   ckan_app_port="$picked"
    fi
  fi
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
      # Created here, so uninstall may remove it (issue #372).
      state_set CKAN_CREATED yes
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
        holder="$(docker ps --format '{{.Names}}\t{{.Ports}}' | awk -v p=":$port->" '$0 ~ p {print $1; exit}')"
        fail "Port $port (CKAN $label) is already in use${holder:+ by container '$holder'}.
       Choose another with --ckan-${label/https/ssl}-port, or stop what is using it."
      fi
    done
    ok "Ports $ckan_ssl_port, $ckan_http_port and $ckan_app_port are free"

    info "Building and starting CKAN — this takes several minutes the first time"
    rc=0
    compose_up CKAN "$ckan_dir" "${COMPOSE[@]}" up -d --build || rc=$?
    [[ $rc -eq 124 ]] && compose_stalled CKAN "$ckan_dir"
    [[ $rc -eq 0 ]] || fail "CKAN failed to start. Inspect it with: cd $ckan_dir && ${COMPOSE[*]} logs"

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
    state_set CKAN_DIR "$ckan_dir"
    state_set CKAN_SYSADMIN "$ckan_sysadmin"
    state_set CKAN_PASSWORD "$ckan_password"
    ok "Token minted and saved to $(basename "$STATE_FILE") so re-running does not create another"
  fi

  put CKAN_LOCAL_ENABLED "True"
  put CKAN_URL "$ckan_site_url"
  put CKAN_API_KEY "$ckan_api_key"
  # CKAN is served over https with a self-signed certificate. Said, not done
  # silently: the operator should know certificate checks are off (#375).
  put CKAN_VERIFY_SSL "False"
  warn "CKAN_VERIFY_SSL=False: the CKAN installed here has a self-signed certificate, so the
       Endpoint does not verify it. Fine on a private network; see docs/configuration.md."
  ckan_url="$ckan_site_url"
fi

# Access requests are stored in MongoDB, read through
# MONGODB_CONNECTION_STRING, whatever the catalog backend is — so wanting them
# means wanting a MongoDB. The catalog provides one on the MongoDB backends;
# on CKAN or with no catalog at all, one is installed for this alone, which is
# the part that was missing: the setting existed and nothing stood up what it
# needs.
if [[ "$want_access_requests" == "yes" ]]; then
  put ENABLE_ACCESS_REQUESTS "True"

  if [[ "$backend" == "mongodb" && -n "$mongodb_url" ]]; then
    ok "Access requests enabled, stored in the MongoDB you provided"
  elif [[ "$backend" == "mongodb" ]]; then
    ok "Access requests enabled, stored in the MongoDB installed for the catalog"
  else
    profiles+=("mongodb")
    bundled_mongodb_password
    ok "Access requests enabled — installing MongoDB for them (compose profile 'mongodb')"
  fi
fi

# S3 object storage. With an endpoint given, point at that existing service;
# otherwise install the bundled MinIO (compose profile 's3'), started with the
# keys bundled_minio_keys gives the Endpoint. The default put of
# S3_ENABLED "False" above is what leaves it off when S3 was not chosen.
if [[ "$want_s3" == "yes" ]]; then
  put S3_ENABLED "True"
  if [[ -n "$s3_endpoint" ]]; then
    [[ -n "$s3_access_key" && -n "$s3_secret_key" ]] \
      || fail "--s3-endpoint requires --s3-access-key and --s3-secret-key."
    put S3_ENDPOINT "$s3_endpoint"
    put S3_ACCESS_KEY "$s3_access_key"
    put S3_SECRET_KEY "$s3_secret_key"
    put S3_REGION "$s3_region"
    put S3_SECURE "$s3_secure"
    ok "S3 enabled, using the S3 at $s3_endpoint"
  else
    profiles+=("s3")
    put S3_ENDPOINT "minio:9000"
    bundled_minio_keys
    put S3_SECURE "False"
    put S3_REGION "us-east-1"
    ok "S3 enabled — installing MinIO (compose profile 's3')"
  fi
fi

if [[ "${fed_streaming:-false}" == "true" ]]; then
  profiles+=("kafka")
  info "Streaming enabled by the registration — adding the 'kafka' profile"
fi

# A named instance runs as its own Compose project with its own container
# names, and the bundled services it starts get free host ports, so it can sit
# next to another Endpoint (issue #355). The ports are kept in the install
# state: a re-run finds them taken by this instance and must not move them.
if [[ "$instance" != "ndp" ]]; then
  put EP_INSTANCE "$instance"
  put COMPOSE_PROJECT_NAME "ndp-ep-$instance"
  host_port() {
    # host_port VARIABLE DEFAULT
    pick_port "$1" "$2"
    put "$1" "$picked"
  }
  for profile in $(printf '%s\n' "${profiles[@]:-}" | sort -u); do
    case "$profile" in
      mongodb) host_port MONGODB_HOST_PORT 27018 ;;
      s3)      host_port MINIO_HOST_PORT 9002
               host_port MINIO_CONSOLE_HOST_PORT 9003 ;;
      kafka)   host_port KAFKA_HOST_PORT 9094
               host_port KAFKA_INTERNAL_HOST_PORT 9095
               host_port KAFKA_UI_HOST_PORT 8081 ;;
    esac
  done
  [[ "$dry_run" == "true" ]] || state_set EP_INSTANCE "$instance"
  ok "Instance '$instance': containers ${instance}-…, Compose project ndp-ep-$instance"
fi

# Which installer this is, for support and for a later status (issue #371).
installer_version="$(git -C "$REPO_ROOT" describe --tags --always 2>/dev/null || echo unknown)"
[[ "$dry_run" == "true" ]] || state_set INSTALLER_VERSION "$installer_version"
# The published port, which status and start report (issue #372).
[[ "$dry_run" == "true" ]] || state_set EP_API_PORT "$ep_api_port"

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

# The staging catalog accepts a dataset only in an organization its token may
# write to. That organization is derived above from the configuration id, so
# ask the staging catalog whether it agrees — a mismatch here is a publish that
# fails much later with an authorization error naming a user, which reads as a
# credentials problem and is not one.
pre_url="$(grep -E '^PRE_CKAN_URL=' "$target" | head -1 | cut -d= -f2- | tr -d '"')"
pre_key="$(grep -E '^PRE_CKAN_API_KEY=' "$target" | head -1 | cut -d= -f2- | tr -d '"')"
pre_org="$(grep -E '^PRE_CKAN_ORGANIZATION=' "$target" | head -1 | cut -d= -f2- | tr -d '"')"

if [[ -n "$pre_url" && -n "$pre_key" && -n "$pre_org" && "$dry_run" != "true" ]]; then
  writable="$(curl -s -m 20 -H "Authorization: $pre_key" \
    "${pre_url%/}/api/3/action/organization_list_for_user?permission=create_dataset" \
    | python3 -c 'import json,sys
try:
    print(" ".join(o.get("name","") for o in json.load(sys.stdin).get("result", [])))
except Exception:
    print("")' 2>/dev/null || echo "")"

  if [[ -z "$writable" ]]; then
    warn "Could not ask the staging catalog which organizations its token may write to."
  elif [[ " $writable " == *" $pre_org "* ]]; then
    ok "Staging catalog accepts publishing to '$pre_org'"
  else
    warn "The staging catalog does not list '$pre_org' among the organizations its"
    warn "token may write to, so publishing there will be refused. Set"
    warn "PRE_CKAN_ORGANIZATION to one of: $writable"
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
  echo "    cd $REPO_ROOT && EP_API_PORT=$ep_api_port ${COMPOSE[*]} ${profiles[*]/#/--profile } up -d --build"
  exit 0
fi

if (exec 3<>"/dev/tcp/127.0.0.1/$ep_api_port") 2>/dev/null; then
  holder="$(docker ps --format '{{.Names}}\t{{.Ports}}' | awk -v p=":$ep_api_port->" '$0 ~ p {print $1; exit}')"
  # Re-running the installer is how an Endpoint is upgraded, and the port is
  # then held by this checkout's own Endpoint container -- the one the
  # "up -d --build" below replaces. That is not a conflict (issue #332).
  holder_dir=""
  if [[ "$holder" == "${instance}-ep-api" ]]; then
    holder_dir="$(docker inspect -f '{{ index .Config.Labels "com.docker.compose.project.working_dir" }}' "$holder" 2>/dev/null || true)"
  fi
  if [[ -n "$holder_dir" && "$(cd "$holder_dir" 2>/dev/null && pwd -P)" == "$(cd "$REPO_ROOT" && pwd -P)" ]]; then
    info "Port $ep_api_port is held by this Endpoint's running container; it will be replaced."
  else
    fail "Port $ep_api_port is already in use${holder:+ by container '$holder'}.
       Choose another with --ep-api-port, or stop what is using it."
  fi
fi

profile_args=()
for profile in "${profiles[@]:-}"; do
  [[ -n "$profile" ]] && profile_args+=(--profile "$profile")
done

cd "$REPO_ROOT"

# --build, or compose reuses whatever image was built the first time this
# machine ran an Endpoint and the checkout is never compiled in: the install
# reports success while running old code, with the freshly rendered .env
# making the mismatch look like a configuration problem. Unchanged sources
# come from the layer cache, so this costs little after the first run.
info "Building the image from this checkout; the first run takes a few minutes."
rc=0
compose_up "the Endpoint" "$REPO_ROOT" \
  env EP_API_PORT="$ep_api_port" "${COMPOSE[@]}" "${profile_args[@]}" up -d --build || rc=$?
[[ $rc -eq 124 ]] && compose_stalled "the Endpoint" "$REPO_ROOT"
[[ $rc -eq 0 ]] || fail "Docker Compose could not start the Endpoint (exit $rc). Inspect it with: cd $REPO_ROOT && ${COMPOSE[*]} logs"

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
