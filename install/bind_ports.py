"""
Publish every port of a Compose file on one address (issue #418).

Compose publishes a port written ``"8002:80"`` on every interface, IPv4 and
IPv6. On a host where a reverse proxy or tunnel fronts the Endpoint, that puts
its API, the bundled CKAN's login page and any bundled database on the whole
network.

``install.sh --bind <address>`` writes a ``docker-compose.override.yml`` next
to each Compose file it runs (the Endpoint's, and the bundled CKAN's). Compose
reads that file by itself, and ``!override`` replaces each service's port list
instead of adding to it (Compose 2.24 or later). The ports are taken from the
Compose file itself, so nothing here has to be kept in step with it; an
address already in front of a port (the CKAN project writes ``0.0.0.0:``) is
replaced.

Without ``--bind`` the Compose files are used as they are, which keeps the
default exactly as before, IPv6 included.
"""

import ipaddress
import re
import sys

# The first line of every file this writes. A docker-compose.override.yml
# without it is the operator's own, and is never replaced or removed.
MARKER = "# Written by install.sh for --bind (issue #418)."

_SERVICE = re.compile(r"^  ([A-Za-z0-9._-]+):\s*(#.*)?$")
_PORTS = re.compile(r"^    ports:\s*(#.*)?$")
_ITEM = re.compile(r"^      - +([\"']?)([^\"'#]+?)\1\s*(#.*)?$")
_ADDRESS_PREFIX = re.compile(r"^(\d{1,3}(\.\d{1,3}){3}|\[[0-9A-Fa-f:]+\]):")


def valid_address(address):
    """True for an IPv4 or IPv6 address, which is all --bind accepts."""
    try:
        ipaddress.ip_address(address)
    except ValueError:
        return False
    return True


def published_ports(compose_text):
    """
    The ports each service publishes, as ``{service: [port, ...]}``.

    Reads the two-space ``services:`` layout both Compose files use; a port
    list item is a quoted or bare string such as ``"${EP_API_PORT:-8002}:80"``.
    """
    ports = {}
    service = None
    in_services = False
    in_ports = False
    for line in compose_text.splitlines():
        if re.match(r"^\S", line):
            in_services = line.startswith("services:")
            service, in_ports = None, False
            continue
        if not in_services:
            continue
        match = _SERVICE.match(line)
        if match:
            service, in_ports = match.group(1), False
            continue
        if _PORTS.match(line):
            in_ports = service is not None
            continue
        if in_ports:
            item = _ITEM.match(line)
            if item:
                ports.setdefault(service, []).append(item.group(2).strip())
            elif line.strip() and not line.strip().startswith("#"):
                in_ports = False
    return ports


def override(compose_text, address):
    """The override file that publishes every port of compose_text on address."""
    host = f"[{address}]" if ":" in address else address
    lines = [MARKER, "# Re-run the installer to change it; do not edit.", "services:"]
    for service, ports in published_ports(compose_text).items():
        lines.append(f"  {service}:")
        lines.append("    ports: !override")
        for port in ports:
            lines.append(f'      - "{host}:{_ADDRESS_PREFIX.sub("", port)}"')
    return "\n".join(lines) + "\n"


def main(argv):
    """bind_ports.py COMPOSE_FILE ADDRESS — print the override for ADDRESS."""
    compose_file, address = argv
    if not valid_address(address):
        print(f"not an IP address: {address}", file=sys.stderr)
        return 2
    with open(compose_file, encoding="utf-8") as handle:
        sys.stdout.write(override(handle.read(), address))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
