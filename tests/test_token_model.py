# tests/test_token_model.py
import pytest
from pydantic import ValidationError

from api.models.token_model import Token, TokenData


class TestTokenModel:
    """Test cases for Token model."""

    def test_token_creation_success(self):
        """Test successful Token creation with valid data."""
        token_data = {
            "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIiwiaWF0IjoxNTE2MjM5MDIyfQ.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c",
            "token_type": "bearer",
        }

        token = Token(**token_data)

        assert token.access_token == token_data["access_token"]
        assert token.token_type == token_data["token_type"]

    def test_token_missing_access_token(self):
        """Test Token creation fails when access_token is missing."""
        token_data = {"token_type": "bearer"}

        with pytest.raises(ValidationError) as exc_info:
            Token(**token_data)

        assert "access_token" in str(exc_info.value)

    def test_token_missing_token_type(self):
        """Test Token creation fails when token_type is missing."""
        token_data = {"access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."}

        with pytest.raises(ValidationError) as exc_info:
            Token(**token_data)

        assert "token_type" in str(exc_info.value)

    def test_token_empty_values(self):
        """Test Token creation allows empty string values (Pydantic default behavior)."""
        # Pydantic allows empty strings by default for string fields
        token1 = Token(access_token="", token_type="bearer")
        assert token1.access_token == ""
        assert token1.token_type == "bearer"

        token2 = Token(access_token="valid_token", token_type="")
        assert token2.access_token == "valid_token"
        assert token2.token_type == ""

    def test_token_model_dict(self):
        """Test Token model can be converted to dictionary."""
        token = Token(access_token="test_token_123", token_type="bearer")

        token_dict = token.model_dump()

        assert token_dict == {"access_token": "test_token_123", "token_type": "bearer"}


class TestTokenDataModel:
    """Test cases for TokenData model."""

    def test_token_data_creation_with_username(self):
        """Test successful TokenData creation with username."""
        token_data = TokenData(username="user123")

        assert token_data.username == "user123"

    def test_token_data_creation_without_username(self):
        """Test TokenData creation with None username (default)."""
        token_data = TokenData()

        assert token_data.username is None

    def test_token_data_creation_explicit_none(self):
        """Test TokenData creation with explicit None username."""
        token_data = TokenData(username=None)

        assert token_data.username is None

    def test_token_data_empty_string_username(self):
        """Test TokenData creation with empty string username."""
        token_data = TokenData(username="")

        assert token_data.username == ""

    def test_token_data_model_dict(self):
        """Test TokenData model can be converted to dictionary."""
        token_data = TokenData(username="testuser")

        data_dict = token_data.model_dump()

        assert data_dict == {"username": "testuser"}

    def test_token_data_model_dict_none(self):
        """Test TokenData model dict with None username."""
        token_data = TokenData(username=None)

        data_dict = token_data.model_dump()

        assert data_dict == {"username": None}

    def test_token_data_field_validation(self):
        """Test TokenData accepts various string types."""
        # Test with regular string
        token_data1 = TokenData(username="regular_user")
        assert token_data1.username == "regular_user"

        # Test with numeric string
        token_data2 = TokenData(username="12345")
        assert token_data2.username == "12345"

        # Test with special characters
        token_data3 = TokenData(username="user@domain.com")
        assert token_data3.username == "user@domain.com"
