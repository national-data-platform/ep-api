"""
The nginx configuration entrypoint.sh generates keeps the client's port
(issue #319).

FastAPI builds its trailing-slash redirects (/status -> /status/) from the Host
header nginx forwards. With ``Host $host`` the port was dropped and clients
were sent to port 80. entrypoint.sh writes to system paths, so these tests read
the configuration it would generate rather than running it; the behaviour is
verified against a built image.
"""

import re
from pathlib import Path

ENTRYPOINT = Path(__file__).resolve().parents[1] / "entrypoint.sh"


def _proxy_blocks():
    """The text of each generated ``location`` that proxies to uvicorn."""
    text = ENTRYPOINT.read_text(encoding="utf-8")
    # Split on the location directives themselves; their paths contain
    # ${ROOT_PATH}, so braces cannot delimit the blocks.
    blocks = re.split(r"\n\s*location ", text)[1:]
    return [block for block in blocks if "proxy_pass" in block.split("\n}")[0]]


def test_every_proxied_location_forwards_host_with_its_port():
    blocks = _proxy_blocks()

    assert blocks, "entrypoint.sh no longer generates proxied locations"
    for block in blocks:
        assert "proxy_set_header Host \\$http_host;" in block, block


def test_no_proxied_location_forwards_host_without_its_port():
    for block in _proxy_blocks():
        assert "proxy_set_header Host \\$host;" not in block, block
