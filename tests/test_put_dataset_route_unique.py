"""
``PUT /dataset/{dataset_id}`` must be documented as the handler that runs.

``api/main.py`` used to mount it twice: ``put_general_dataset`` through
``update_router``, and ``put_dataset`` as a separate router after it. Requests
reached the first, but the later registration overwrote the first in the
OpenAPI schema, so Swagger documented a body and a guard that were never
applied (#301).

The routes are mounted at import time and only when a local catalog is
enabled, so the app is imported in a subprocess with that switched on, which
keeps the import-time settings of the rest of the suite untouched.
"""

import json
import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

SCRIPT = """
import json
from api.main import app
op = app.openapi()["paths"]["/dataset/{dataset_id}"]["put"]
body = op["requestBody"]["content"]["application/json"]["schema"]["$ref"]
print(json.dumps({"summary": op.get("summary"), "body": body}))
"""


def test_put_dataset_documents_the_handler_that_runs():
    env = {
        **os.environ,
        "CKAN_LOCAL_ENABLED": "True",
        "LOCAL_CATALOG_BACKEND": "ckan",
        "CKAN_URL": "http://ckan.invalid",
    }
    result = subprocess.run(
        [sys.executable, "-c", SCRIPT],
        cwd=REPO_ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert result.returncode == 0, result.stderr

    op = json.loads(result.stdout.strip().splitlines()[-1])

    assert op["summary"] == "Update an existing general dataset"
    assert op["body"].endswith("/GeneralDatasetUpdateRequest")
