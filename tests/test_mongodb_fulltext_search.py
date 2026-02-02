# tests/test_mongodb_fulltext_search.py
"""
Tests for MongoDB full-text search functionality.
"""

import pytest
from unittest.mock import Mock, MagicMock, patch, call
from pymongo import ASCENDING

from api.repositories.mongodb_repository import MongoDBRepository


class TestMongoDBFullTextSearch:
    """Test cases for MongoDB full-text search implementation."""

    @pytest.fixture
    def mock_client(self):
        """Create a mock MongoDB client."""
        client = Mock()
        db = Mock()
        packages = Mock()
        resources = Mock()
        organizations = Mock()

        client.__getitem__ = Mock(return_value=db)
        db.packages = packages
        db.resources = resources
        db.organizations = organizations

        return client, db, packages, resources, organizations

    @pytest.fixture
    def repository(self, mock_client):
        """Create a MongoDB repository with mocked client."""
        client, db, packages, resources, organizations = mock_client

        with patch(
            "api.repositories.mongodb_repository.MongoClient", return_value=client
        ):
            repo = MongoDBRepository(
                connection_string="mongodb://localhost:27017", database_name="test_db"
            )
            return repo

    def test_create_indexes_includes_tags_with_weights(self, repository):
        """Test that text index is created with tags and proper weights."""
        packages_mock = repository.packages

        # Check that create_index was called with the text index
        calls = packages_mock.create_index.call_args_list

        # Find the call that creates the fulltext search index
        fulltext_call = None
        for c in calls:
            if len(c[0]) > 0 and isinstance(c[0][0], list):
                # Check if it's the text index call
                index_spec = c[0][0]
                if any("text" in str(field) for field in index_spec):
                    fulltext_call = c
                    break

        assert fulltext_call is not None, "Full-text index should be created"

        # Verify the index includes title, tags, and notes
        index_spec = fulltext_call[0][0]
        fields = [field[0] for field in index_spec]
        assert "title" in fields
        assert "tags" in fields
        assert "notes" in fields

        # Verify weights are specified
        assert "weights" in fulltext_call[1]
        weights = fulltext_call[1]["weights"]
        assert weights["title"] == 10
        assert weights["tags"] == 5
        assert weights["notes"] == 1

    def test_package_search_uses_text_operator_for_simple_query(self, repository):
        """Test that simple text queries use $text operator."""
        packages_mock = repository.packages
        organizations_mock = repository.organizations

        # Create a proper mock cursor chain
        mock_cursor = Mock()
        mock_after_sort = Mock()
        mock_after_skip = Mock()
        mock_after_limit = []

        mock_cursor.sort = Mock(return_value=mock_after_sort)
        mock_after_sort.skip = Mock(return_value=mock_after_skip)
        mock_after_skip.limit = Mock(return_value=mock_after_limit)

        packages_mock.find = Mock(return_value=mock_cursor)
        packages_mock.count_documents = Mock(return_value=0)
        organizations_mock.find_one = Mock(return_value=None)

        repository.package_search(q="climate data")

        # Verify $text operator was used
        call_args = packages_mock.find.call_args
        query = call_args[0][0]

        assert "$text" in query
        assert query["$text"]["$search"] == "climate data"

    def test_package_search_includes_score_projection(self, repository):
        """Test that text search includes score projection."""
        packages_mock = repository.packages
        mock_cursor = Mock()
        mock_cursor.skip = Mock(return_value=mock_cursor)
        mock_cursor.limit = Mock(return_value=[])
        mock_cursor.sort = Mock(return_value=mock_cursor)

        packages_mock.find = Mock(return_value=mock_cursor)
        packages_mock.count_documents = Mock(return_value=0)

        repository.package_search(q="climate")

        # Verify projection was passed to find()
        call_args = packages_mock.find.call_args
        if len(call_args[0]) > 1:
            projection = call_args[0][1]
            assert "score" in projection
            assert projection["score"] == {"$meta": "textScore"}

    def test_package_search_sorts_by_score_for_text_queries(self, repository):
        """Test that text search results are sorted by relevance score."""
        packages_mock = repository.packages
        mock_cursor = Mock()
        mock_cursor.skip = Mock(return_value=mock_cursor)
        mock_cursor.limit = Mock(return_value=[])
        mock_cursor.sort = Mock(return_value=mock_cursor)

        packages_mock.find = Mock(return_value=mock_cursor)
        packages_mock.count_documents = Mock(return_value=0)

        repository.package_search(q="climate")

        # Verify sort was called with score
        mock_cursor.sort.assert_called_once()
        sort_args = mock_cursor.sort.call_args[0][0]

        # First sort criterion should be by score
        assert len(sort_args) > 0
        assert sort_args[0][0] == "score"
        assert sort_args[0][1] == {"$meta": "textScore"}

    def test_package_search_preserves_field_queries(self, repository):
        """Test that Solr-style field queries still work."""
        packages_mock = repository.packages
        organizations_mock = repository.organizations

        mock_cursor = Mock()
        mock_cursor.skip = Mock(return_value=mock_cursor)
        mock_cursor.limit = Mock(return_value=[])
        mock_cursor.sort = Mock(return_value=mock_cursor)

        packages_mock.find = Mock(return_value=mock_cursor)
        packages_mock.count_documents = Mock(return_value=0)
        organizations_mock.find_one = Mock(
            return_value={"id": "org-123", "name": "test-org"}
        )

        repository.package_search(q="organization:test-org")

        # Verify field query is used, not $text
        call_args = packages_mock.find.call_args
        query = call_args[0][0]

        assert "$text" not in query
        assert "owner_org" in query
        assert query["owner_org"] == "org-123"

    def test_package_search_text_search_with_special_characters(self, repository):
        """Test that text search handles special characters."""
        packages_mock = repository.packages
        organizations_mock = repository.organizations

        # Create a proper mock cursor chain
        mock_cursor = Mock()
        mock_after_sort = Mock()
        mock_after_skip = Mock()
        mock_after_limit = []

        mock_cursor.sort = Mock(return_value=mock_after_sort)
        mock_after_sort.skip = Mock(return_value=mock_after_skip)
        mock_after_skip.limit = Mock(return_value=mock_after_limit)

        packages_mock.find = Mock(return_value=mock_cursor)
        packages_mock.count_documents = Mock(return_value=0)
        organizations_mock.find_one = Mock(return_value=None)

        repository.package_search(q="climate & weather")

        # Verify $text operator was used
        call_args = packages_mock.find.call_args
        query = call_args[0][0]

        assert "$text" in query
        assert query["$text"]["$search"] == "climate & weather"

    def test_package_search_empty_query_returns_all(self, repository):
        """Test that empty or wildcard query returns all packages."""
        packages_mock = repository.packages
        organizations_mock = repository.organizations

        # Create a proper mock cursor chain (needs sort for default sorting)
        mock_cursor = Mock()
        mock_after_sort = Mock()
        mock_after_skip = Mock()
        mock_after_limit = []

        mock_cursor.sort = Mock(return_value=mock_after_sort)
        mock_after_sort.skip = Mock(return_value=mock_after_skip)
        mock_after_skip.limit = Mock(return_value=mock_after_limit)

        packages_mock.find = Mock(return_value=mock_cursor)
        packages_mock.count_documents = Mock(return_value=0)
        organizations_mock.find_one = Mock(return_value=None)

        repository.package_search(q="*:*")

        # Verify no text search is applied
        call_args = packages_mock.find.call_args
        query = call_args[0][0]

        assert "$text" not in query
        assert len(query) == 0  # Empty query

    def test_package_search_combines_text_and_filters(self, repository):
        """Test that text search can be combined with filter queries."""
        packages_mock = repository.packages
        organizations_mock = repository.organizations

        # Create a proper mock cursor chain
        mock_cursor = Mock()
        mock_after_sort = Mock()
        mock_after_skip = Mock()
        mock_after_limit = []

        mock_cursor.sort = Mock(return_value=mock_after_sort)
        mock_after_sort.skip = Mock(return_value=mock_after_skip)
        mock_after_skip.limit = Mock(return_value=mock_after_limit)

        packages_mock.find = Mock(return_value=mock_cursor)
        packages_mock.count_documents = Mock(return_value=0)
        organizations_mock.find_one = Mock(return_value=None)

        repository.package_search(q="climate", fq="type:dataset")

        # Verify both text search and filters are applied
        call_args = packages_mock.find.call_args
        query = call_args[0][0]

        assert "$text" in query
        assert "type" in query
        assert query["type"] == "dataset"

    def test_package_search_pagination_with_text_search(self, repository):
        """Test that pagination works correctly with text search."""
        packages_mock = repository.packages
        mock_cursor = Mock()
        mock_cursor.skip = Mock(return_value=mock_cursor)
        mock_cursor.limit = Mock(return_value=[])
        mock_cursor.sort = Mock(return_value=mock_cursor)

        packages_mock.find = Mock(return_value=mock_cursor)
        packages_mock.count_documents = Mock(return_value=100)

        repository.package_search(q="climate", rows=20, start=40)

        # Verify skip and limit are applied
        mock_cursor.skip.assert_called_once_with(40)
        mock_cursor.limit.assert_called_once_with(20)
