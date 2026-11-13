"""``POST /search`` keeps the organization when a search term is given (#427).

With ``search_term`` set, the query became the term alone and ``owner_org``
was never looked at, so the Search page's organization filter, which sends
both when a term is typed, listed other organizations' datasets too:
``{"owner_org": "opentopography", "search_term": "lidar"}`` returned 985
datasets from the global catalog, 844 of them from ``usgs-3dep``.

The organization is now sent to the catalog as a filter query alongside the
term, so the paging and ``X-Total-Count`` count that organization only.
"""

from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from api.main import app
from api.repositories.ckan_repository import CKANRepository
from api.services.datasource_services.search_datasource import (
    search_datasource_page,
)

CATALOG = "api.services.datasource_services.search_datasource.catalog_settings"


def _dataset(i, org, title):
    return {
        "id": f"id-{i}",
        "name": f"dataset-{i}",
        "title": title,
        "notes": None,
        "organization": {"name": org},
        "resources": [
            {"id": f"res-{i}", "url": f"https://example.org/{i}", "name": "r"}
        ],
        "extras": [],
    }


class Catalog(CKANRepository):
    """A stand-in CKAN catalog that applies the term and ``organization:``."""

    def __init__(self):
        self.datasets = (
            [_dataset(i, "usgs-3dep", f"Lidar {i}") for i in range(0, 30)]
            + [_dataset(i, "opentopography", f"Lidar {i}") for i in range(30, 40)]
            + [_dataset(i, "opentopography", f"Raster {i}") for i in range(40, 45)]
        )
        self.calls = []

    def package_search(self, q="*:*", rows=10, start=0, fq_list=None, **kwargs):
        self.calls.append({"q": q, "fq_list": list(fq_list or [])})
        matches = self.datasets
        for clause in [q] + list(fq_list or []):
            if clause == "*:*":
                continue
            if clause.startswith("organization:"):
                org = clause.split(":", 1)[1].strip('"')
                matches = [d for d in matches if d["organization"]["name"] == org]
            else:
                matches = [d for d in matches if clause.lower() in d["title"].lower()]
        return {"count": len(matches), "results": matches[start : start + rows]}


@pytest.fixture
def catalog():
    repo = Catalog()
    with patch(CATALOG) as settings:
        settings.global_catalog = repo
        settings.local_catalog = repo
        yield repo


@pytest.mark.asyncio
async def test_the_organization_is_kept_with_a_search_term(catalog):
    results, total = await search_datasource_page(
        owner_org="opentopography", search_term="lidar", server="global"
    )

    assert {r.organization_id for r in results} == {"opentopography"}
    assert len(results) == 10
    assert total == 10


@pytest.mark.asyncio
async def test_the_organization_goes_to_the_catalog(catalog):
    await search_datasource_page(
        owner_org="opentopography", search_term="lidar", server="global"
    )

    assert all(
        'organization:"opentopography"' in call["fq_list"] for call in catalog.calls
    ), catalog.calls


@pytest.mark.asyncio
async def test_a_term_alone_still_searches_every_organization(catalog):
    results, total = await search_datasource_page(search_term="lidar", server="global")

    assert {r.organization_id for r in results} == {"usgs-3dep", "opentopography"}
    assert total == 40


@pytest.mark.asyncio
async def test_the_organization_alone_is_unchanged(catalog):
    results, total = await search_datasource_page(
        owner_org="opentopography", server="global"
    )

    assert len(results) == 15
    assert total == 15


def test_the_route_counts_the_organization_only(catalog):
    response = TestClient(app).post(
        "/search",
        json={
            "owner_org": "opentopography",
            "search_term": "lidar",
            "server": "global",
        },
    )

    assert response.status_code == 200, response.text
    assert {d["owner_org"] for d in response.json()} == {"opentopography"}
    assert response.headers["X-Total-Count"] == "10"
