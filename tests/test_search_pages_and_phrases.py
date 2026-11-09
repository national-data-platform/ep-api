"""Searching a large catalog asks for what it can serve (issue #402).

The search used to ask CKAN for 1000 full datasets in one request, with each
term unquoted. On the global catalog ``macav2`` matched 4224 datasets (CKAN
splits it into ``macav`` and ``2``), the request hit the proxy's timeout, and
the answer was reported as "Global catalog is not reachable".
"""

from unittest.mock import MagicMock, patch

import pytest
from ckanapi import CKANAPIError
from fastapi import HTTPException

from api.services.datasource_services.search_datasets_by_terms import (
    MAX_DATASETS,
    PAGE_SIZE,
    search_datasets_by_terms,
    solr_phrase,
)

CATALOG = "api.services.datasource_services.search_datasets_by_terms.catalog_settings"


def _dataset(i, text="water"):
    return {
        "id": f"id-{i}",
        "name": f"dataset-{i}",
        "title": f"{text} {i}",
        "notes": None,
        "resources": [],
        "extras": [],
    }


class PagedCatalog:
    """A stand-in catalog serving ``total`` matching datasets page by page."""

    def __init__(self, total, text="water"):
        self.datasets = [_dataset(i, text) for i in range(total)]
        self.calls = []

    def package_search(self, q="*:*", rows=10, start=0, **kwargs):
        self.calls.append({"q": q, "rows": rows, "start": start})
        return {
            "count": len(self.datasets),
            "results": self.datasets[start : start + rows],
        }


async def _search(repo, terms, keys=None, server="global"):
    with patch(CATALOG) as catalog:
        catalog.global_catalog = repo
        catalog.local_catalog = repo
        catalog.pre_catalog = repo
        return await search_datasets_by_terms(terms, keys_list=keys, server=server)


@pytest.mark.asyncio
async def test_no_request_asks_for_more_than_a_page():
    repo = PagedCatalog(370)

    results = await _search(repo, ["water"])

    assert len(results) == 370
    assert all(call["rows"] <= PAGE_SIZE for call in repo.calls)
    assert [call["start"] for call in repo.calls] == [0, 100, 200, 300]


@pytest.mark.asyncio
async def test_no_more_datasets_are_looked_at_than_before():
    repo = PagedCatalog(4224)

    results = await _search(repo, ["water"])

    assert len(results) == MAX_DATASETS
    assert repo.calls[-1]["start"] == MAX_DATASETS - PAGE_SIZE


@pytest.mark.asyncio
async def test_an_empty_answer_is_one_request():
    repo = PagedCatalog(0)

    assert await _search(repo, ["macav2"]) == []
    assert len(repo.calls) == 1


@pytest.mark.asyncio
async def test_a_catalog_without_a_count_stops_at_a_short_page():
    repo = MagicMock()
    repo.package_search.side_effect = [
        {"results": [_dataset(i) for i in range(100)]},
        {"results": [_dataset(i) for i in range(100, 130)]},
    ]

    results = await _search(repo, ["water"])

    assert len(results) == 130
    assert repo.package_search.call_count == 2


@pytest.mark.asyncio
async def test_each_term_is_searched_as_a_phrase():
    repo = PagedCatalog(0)

    await _search(repo, ["macav2", "great salt lake"])

    assert repo.calls[0]["q"] == '"macav2" AND "great salt lake"'


@pytest.mark.asyncio
async def test_a_keyed_term_is_a_phrase_in_that_field():
    repo = PagedCatalog(0)

    await _search(repo, ["macav2", "water"], keys=["title", None])

    assert repo.calls[0]["q"] == 'title:"macav2" AND "water"'


def test_quotes_and_backslashes_inside_a_term_are_escaped():
    assert solr_phrase('say "hi"') == '"say \\"hi\\""'
    assert solr_phrase("a\\b") == '"a\\\\b"'


@pytest.mark.asyncio
async def test_a_catalog_error_is_not_called_unreachable():
    repo = MagicMock()
    repo.package_search.side_effect = CKANAPIError("504 Gateway Time-out")

    with pytest.raises(HTTPException) as error:
        await _search(repo, ["macav2"])

    assert error.value.status_code == 503
    assert "not reachable" not in error.value.detail
    assert "Global catalog could not answer this search" in error.value.detail


@pytest.mark.asyncio
async def test_the_datasets_are_not_printed(capsys):
    await _search(PagedCatalog(3), ["water"])

    assert capsys.readouterr().out == ""
