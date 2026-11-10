"""Search results a page at a time, with the number of matches (issue #420).

``GET /search`` looked at no more than the first 1000 matching datasets and
said nothing about the rest: ``GNSS`` matched 1124 on the global catalog, so
124 could not be reached. It now takes ``limit`` and ``offset`` and reports
the catalog's number of matches in ``X-Total-Count``. The body is still a
list, so existing clients are unaffected.
"""

from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from api.main import app
from api.repositories.ckan_repository import CKANRepository
from api.services.datasource_services.search_datasets_by_terms import (
    MAX_DATASETS,
    PAGE_SIZE,
    search_datasets_page,
)

CATALOG = "api.services.datasource_services.search_datasets_by_terms.catalog_settings"


class PagedCatalog(CKANRepository):
    """A stand-in CKAN catalog serving ``total`` matching datasets."""

    def __init__(self, total):
        self.datasets = [
            {
                "id": f"id-{i}",
                "name": f"dataset-{i}",
                "title": f"gnss {i}",
                "notes": None,
                "resources": [],
                "extras": [],
            }
            for i in range(total)
        ]
        self.calls = []

    def package_search(self, q="*:*", rows=10, start=0, **kwargs):
        self.calls.append({"rows": rows, "start": start})
        return {
            "count": len(self.datasets),
            "results": self.datasets[start : start + rows],
        }


@pytest.fixture
def gnss():
    repo = PagedCatalog(1124)
    with patch(CATALOG) as catalog:
        catalog.global_catalog = repo
        catalog.local_catalog = repo
        yield repo


@pytest.mark.asyncio
async def test_a_page_starts_where_it_is_asked_to(gnss):
    results, total = await search_datasets_page(["gnss"], offset=200, limit=50)

    assert [r.name for r in results] == [f"dataset-{i}" for i in range(200, 250)]
    assert total == 1124
    assert gnss.calls == [{"rows": 50, "start": 200}]


@pytest.mark.asyncio
async def test_a_large_page_is_still_asked_for_100_at_a_time(gnss):
    results, _ = await search_datasets_page(["gnss"], offset=0, limit=250)

    assert len(results) == 250
    assert all(call["rows"] <= PAGE_SIZE for call in gnss.calls)


@pytest.mark.asyncio
async def test_datasets_past_the_first_1000_can_be_reached(gnss):
    results, total = await search_datasets_page(["gnss"], offset=1000, limit=200)

    assert [r.name for r in results][0] == "dataset-1000"
    assert len(results) == 124
    assert total == 1124


def _get(**params):
    return TestClient(app).get("/search", params={"terms": "gnss", **params})


def test_the_route_returns_the_page_and_the_number_of_matches(gnss):
    response = _get(limit=10, offset=1100)

    assert response.status_code == 200, response.text
    assert [d["name"] for d in response.json()] == [
        f"dataset-{i}" for i in range(1100, 1110)
    ]
    assert response.headers["X-Total-Count"] == "1124"


def test_without_paging_it_answers_as_before_and_says_how_many_matched(gnss):
    response = _get()

    assert response.status_code == 200, response.text
    assert len(response.json()) == MAX_DATASETS
    assert response.headers["X-Total-Count"] == "1124"


def test_browsers_on_other_origins_can_read_the_count(gnss):
    response = TestClient(app).get(
        "/search",
        params={"terms": "gnss", "limit": 1},
        headers={"Origin": "https://portal.example.org"},
    )

    assert (
        "x-total-count"
        in response.headers.get("access-control-expose-headers", "").lower()
    )


@pytest.mark.parametrize(
    "params", [{"limit": 0}, {"limit": MAX_DATASETS + 1}, {"offset": -1}]
)
def test_out_of_range_paging_is_refused(gnss, params):
    assert _get(**params).status_code == 422
