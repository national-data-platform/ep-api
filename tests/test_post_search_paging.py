"""``POST /search`` a page at a time, with the number of matches (issue #424).

``POST /search`` (the organization filter and the services list in the UI)
asked the catalog for 1000 full datasets per request, the size that hit the
global catalog's 15 s timeout in #402, and kept asking until nothing came
back, so a broad search read and returned every match in one response.

It now asks for at most 100 datasets per request and takes the same
``offset`` / ``limit`` as ``GET /search`` (#420), reporting the catalog's
number of matches in ``X-Total-Count``. The paging counts the catalog's
matches: the resource and keyword filters applied afterwards can return
fewer than ``limit``, and ``X-Total-Count`` is the number before them.
"""

from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from api.main import app
from api.repositories.ckan_repository import CKANRepository
from api.services.datasource_services.search_datasource import (
    search_datasource,
    search_datasource_page,
)

CATALOG = "api.services.datasource_services.search_datasource.catalog_settings"


class OrgCatalog(CKANRepository):
    """A stand-in CKAN catalog: ``total`` datasets of one organization."""

    def __init__(self, total):
        self.datasets = [
            {
                "id": f"id-{i}",
                "name": f"dataset-{i}",
                "title": f"Dataset {i}",
                "notes": None,
                "organization": {"name": "big-org"},
                "resources": [
                    {
                        "id": f"res-{i}",
                        "url": f"https://example.org/{i}.csv",
                        "name": f"file {i}",
                        "format": "CSV" if i % 2 == 0 else "JSON",
                    }
                ],
                "extras": [],
            }
            for i in range(total)
        ]
        self.calls = []

    def package_search(self, q="*:*", rows=10, start=0, **kwargs):
        self.calls.append({"q": q, "rows": rows, "start": start, **kwargs})
        return {
            "count": len(self.datasets),
            "results": self.datasets[start : start + rows],
        }


@pytest.fixture
def big_org():
    repo = OrgCatalog(1250)
    with patch(CATALOG) as catalog:
        catalog.global_catalog = repo
        catalog.local_catalog = repo
        yield repo


@pytest.mark.asyncio
async def test_the_catalog_is_asked_100_at_a_time(big_org):
    await search_datasource_page(owner_org="big-org", server="global")

    assert big_org.calls, "the catalog was not asked"
    assert all(call["rows"] <= 100 for call in big_org.calls), big_org.calls


@pytest.mark.asyncio
async def test_without_paging_at_most_1000_are_returned(big_org):
    results, total = await search_datasource_page(owner_org="big-org", server="global")

    assert len(results) == 1000
    assert total == 1250


@pytest.mark.asyncio
async def test_a_page_starts_where_it_is_asked_to(big_org):
    results, total = await search_datasource_page(
        owner_org="big-org", server="global", offset=1200, limit=100
    )

    assert [r.name for r in results] == [f"dataset-{i}" for i in range(1200, 1250)]
    assert total == 1250


@pytest.mark.asyncio
async def test_the_paging_counts_catalog_matches_before_the_filters(big_org):
    # Half the datasets have a CSV resource; a page of 100 catalog matches
    # holds 50 of them, and the total is still the catalog's.
    results, total = await search_datasource_page(
        owner_org="big-org",
        resource_format="csv",
        server="global",
        offset=0,
        limit=100,
    )

    assert len(results) == 50
    assert total == 1250


@pytest.mark.asyncio
async def test_a_nearest_in_time_search_still_asks_for_one(big_org):
    await search_datasource_page(timestamp=">2026-01-01", server="global")

    assert [call["rows"] for call in big_org.calls] == [1]
    assert big_org.calls[0]["sort"] == "timestamp asc"


@pytest.mark.asyncio
async def test_the_list_function_keeps_its_signature(big_org):
    results = await search_datasource(owner_org="big-org", server="global")

    assert len(results) == 1000


def _post(body, **params):
    # Without the app's startup (no "with"): the route is all that is tested.
    return TestClient(app).post("/search", json=body, params=params)


def test_the_route_returns_the_page_and_the_number_of_matches(big_org):
    response = _post(
        {"owner_org": "big-org", "server": "global"}, offset=1200, limit=100
    )

    assert response.status_code == 200, response.text
    assert len(response.json()) == 50
    assert response.headers["X-Total-Count"] == "1250"


def test_without_paging_the_body_is_still_a_list(big_org):
    response = _post({"owner_org": "big-org", "server": "global"})

    assert response.status_code == 200, response.text
    assert isinstance(response.json(), list)
    assert len(response.json()) == 1000
    assert response.headers["X-Total-Count"] == "1250"


@pytest.mark.parametrize("params", [{"limit": 0}, {"limit": 1001}, {"offset": -1}])
def test_out_of_range_paging_is_refused(big_org, params):
    response = _post({"owner_org": "big-org", "server": "global"}, **params)

    assert response.status_code == 422
