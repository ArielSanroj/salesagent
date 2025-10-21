#!/usr/bin/env python3
"""
Tests for validators.py - Input validation utilities
"""

# Add src to path for imports
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from exceptions import ValidationError
from validators import ConfigValidator, InputValidator


class TestInputValidator:
    """Test cases for InputValidator"""

    def test_is_valid_email(self):
        """Test email validation"""
        # Valid emails
        assert InputValidator.is_valid_email("test@example.com") is True
        assert InputValidator.is_valid_email("user.name@domain.co.uk") is True
        assert InputValidator.is_valid_email("test+tag@example.org") is True

        # Invalid emails
        assert InputValidator.is_valid_email("invalid-email") is False
        assert InputValidator.is_valid_email("") is False
        assert InputValidator.is_valid_email(None) is False
        assert InputValidator.is_valid_email("@example.com") is False
        assert InputValidator.is_valid_email("test@") is False

    def test_is_valid_url(self):
        """Test URL validation"""
        # Valid URLs
        assert InputValidator.is_valid_url("https://example.com") is True
        assert InputValidator.is_valid_url("http://example.com") is True
        assert InputValidator.is_valid_url("https://www.example.com/path") is True

        # Invalid URLs
        assert InputValidator.is_valid_url("invalid-url") is False
        assert InputValidator.is_valid_url("") is False
        assert InputValidator.is_valid_url(None) is False
        assert InputValidator.is_valid_url("ftp://example.com") is False

    def test_validate_signal_type(self):
        """Test signal type validation"""
        # Valid signal types
        for i in range(1, 7):
            assert InputValidator.validate_signal_type(i) is True

        # Invalid signal types
        assert InputValidator.validate_signal_type(0) is False
        assert InputValidator.validate_signal_type(7) is False
        assert InputValidator.validate_signal_type(-1) is False

    def test_validate_relevance_score(self):
        """Test relevance score validation"""
        # Valid scores
        assert InputValidator.validate_relevance_score(0.0) is True
        assert InputValidator.validate_relevance_score(0.5) is True
        assert InputValidator.validate_relevance_score(1.0) is True

        # Invalid scores
        assert InputValidator.validate_relevance_score(-0.1) is False
        assert InputValidator.validate_relevance_score(1.1) is False

    def test_sanitize_text(self):
        """Test text sanitization"""
        # HTML removal
        html_text = "<p>Hello <b>world</b></p>"
        result = InputValidator.sanitize_text(html_text)
        assert "<" not in result
        assert ">" not in result
        assert "Hello world" in result

        # Whitespace cleanup
        messy_text = "  Hello   world  \n  "
        result = InputValidator.sanitize_text(messy_text)
        assert result == "Hello world"

        # Length truncation
        long_text = "A" * 2000
        result = InputValidator.sanitize_text(long_text, max_length=100)
        assert len(result) == 103  # 100 + "..."
        assert result.endswith("...")

        # Empty input
        assert InputValidator.sanitize_text("") == ""
        assert InputValidator.sanitize_text(None) == ""

    def test_validate_opportunity_data_success(self):
        """Test successful opportunity data validation"""
        data = {
            "title": "Test Title",
            "company": "Test Company",
            "url": "https://example.com",
            "person": "John Doe",
            "email": "john@example.com",
            "signal_type": 1,
            "relevance_score": 0.8,
        }

        result = InputValidator.validate_opportunity_data(data)

        # Check that data was sanitized
        assert result["title"] == "Test Title"
        assert result["company"] == "Test Company"
        assert result["email"] == "john@example.com"

    def test_validate_opportunity_data_missing_fields(self):
        """Test opportunity data validation with missing fields"""
        data = {
            "title": "Test Title",
            # Missing company and url
        }

        with pytest.raises(ValidationError, match="Missing required field"):
            InputValidator.validate_opportunity_data(data)

    def test_validate_opportunity_data_invalid_email(self):
        """Test opportunity data validation with invalid email"""
        data = {
            "title": "Test Title",
            "company": "Test Company",
            "url": "https://example.com",
            "email": "invalid-email",
        }

        result = InputValidator.validate_opportunity_data(data)
        assert result["email"] == "Manual validation needed"

    def test_validate_opportunity_data_invalid_url(self):
        """Test opportunity data validation with invalid URL"""
        data = {"title": "Test Title", "company": "Test Company", "url": "invalid-url"}

        with pytest.raises(ValidationError, match="Invalid URL"):
            InputValidator.validate_opportunity_data(data)

    def test_validate_opportunity_data_invalid_signal_type(self):
        """Test opportunity data validation with invalid signal type"""
        data = {
            "title": "Test Title",
            "company": "Test Company",
            "url": "https://example.com",
            "signal_type": 10,
        }

        with pytest.raises(ValidationError, match="Invalid signal type"):
            InputValidator.validate_opportunity_data(data)

    def test_validate_opportunity_data_invalid_relevance_score(self):
        """Test opportunity data validation with invalid relevance score"""
        data = {
            "title": "Test Title",
            "company": "Test Company",
            "url": "https://example.com",
            "relevance_score": 1.5,
        }

        with pytest.raises(ValidationError, match="Invalid relevance score"):
            InputValidator.validate_opportunity_data(data)


class TestConfigValidator:
    """Test cases for ConfigValidator"""

    @patch("os.getenv")
    def test_validate_required_env_vars_all_present(self, mock_getenv):
        """Test environment variable validation when all are present"""
        mock_getenv.return_value = "test_value"

        missing = ConfigValidator.validate_required_env_vars()
        assert missing == []

    @patch("os.getenv")
    def test_validate_required_env_vars_missing(self, mock_getenv):
        """Test environment variable validation when some are missing"""

        def mock_getenv_side_effect(var):
            if var == "OLLAMA_API_KEY":
                return "test_value"
            return None

        mock_getenv.side_effect = mock_getenv_side_effect

        missing = ConfigValidator.validate_required_env_vars()
        assert len(missing) == 3
        assert "EMAIL_PASSWORD" in missing
        assert "EMAIL_SENDER" in missing
        assert "EMAIL_RECIPIENT" in missing

    def test_validate_api_keys_all_present(self):
        """Test API key validation when all are present"""
        config = {
            "newsdata": {"api_key": "test_key"},
            "hunter": {"api_key": "test_key"},
            "google_sheets": {"api_key": "test_key"},
        }

        missing = ConfigValidator.validate_api_keys(config)
        assert missing == []

    def test_validate_api_keys_missing(self):
        """Test API key validation when some are missing"""
        config = {
            "newsdata": {"api_key": "test_key"},
            "hunter": {},  # Missing api_key
            "google_sheets": {"api_key": "test_key"},
        }

        missing = ConfigValidator.validate_api_keys(config)
        assert "hunter_api_key" in missing

    def test_validate_api_keys_empty_config(self):
        """Test API key validation with empty config"""
        config = {}

        missing = ConfigValidator.validate_api_keys(config)
        assert len(missing) == 0  # No services to check


if __name__ == "__main__":
    pytest.main([__file__])
