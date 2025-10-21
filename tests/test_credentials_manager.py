#!/usr/bin/env python3
"""
Unit tests for Credentials Manager
"""

import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

import yaml

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from credentials_manager import CredentialsManager


class TestCredentialsManager(unittest.TestCase):
    """Test cases for Credentials Manager"""

    def setUp(self):
        """Set up test fixtures"""
        # Create temporary config directory
        self.temp_dir = tempfile.mkdtemp()
        self.config_dir = Path(self.temp_dir) / "config"
        self.config_dir.mkdir()

        # Create test config file
        self.config_file = self.config_dir / "secure_config.yaml"
        test_config = {
            "api": {
                "ollama": {
                    "model": "test-model",
                    "base_url": "https://test.api.com/v1",
                    "timeout": 30,
                    "max_retries": 3,
                    "retry_delay": 2,
                },
                "serpapi": {"timeout": 30, "max_retries": 3},
                "hunter": {"timeout": 30, "max_retries": 3},
            },
            "email_config": {"smtp_server": "smtp.test.com", "smtp_port": 587},
        }

        with open(self.config_file, "w") as f:
            yaml.dump(test_config, f)

    def tearDown(self):
        """Clean up after tests"""
        import shutil

        shutil.rmtree(self.temp_dir)

    @patch.dict(
        os.environ,
        {"OLLAMA_API_KEY": "test-ollama-key", "EMAIL_PASSWORD": "test-email-password"},
    )
    def test_initialization_success(self):
        """Test successful credentials manager initialization"""
        manager = CredentialsManager(str(self.config_dir))

        # Verify config loaded
        self.assertIsNotNone(manager.secure_config)
        self.assertIn("api", manager.secure_config)

    def test_initialization_config_not_found(self):
        """Test initialization with missing config file"""
        with self.assertRaises(FileNotFoundError):
            CredentialsManager("nonexistent_dir")

    @patch.dict(
        os.environ,
        {"OLLAMA_API_KEY": "test-ollama-key", "EMAIL_PASSWORD": "test-email-password"},
    )
    def test_get_ollama_config(self):
        """Test Ollama configuration retrieval"""
        manager = CredentialsManager(str(self.config_dir))
        config = manager.get_ollama_config()

        self.assertEqual(config["api_key"], "test-ollama-key")
        self.assertEqual(config["model"], "test-model")
        self.assertEqual(config["base_url"], "https://test.api.com/v1")

    @patch.dict(os.environ, {})
    def test_get_ollama_config_missing_key(self):
        """Test Ollama configuration with missing API key"""
        manager = CredentialsManager(str(self.config_dir))

        with self.assertRaises(ValueError):
            manager.get_ollama_config()

    @patch.dict(os.environ, {"SERPAPI_KEY": "test-serpapi-key"})
    def test_get_serpapi_config(self):
        """Test SerpAPI configuration retrieval"""
        manager = CredentialsManager(str(self.config_dir))
        config = manager.get_serpapi_config()

        self.assertEqual(config["api_key"], "test-serpapi-key")
        self.assertEqual(config["timeout"], 30)

    @patch.dict(os.environ, {})
    def test_get_serpapi_config_missing_key(self):
        """Test SerpAPI configuration with missing API key"""
        manager = CredentialsManager(str(self.config_dir))
        config = manager.get_serpapi_config()

        self.assertIsNone(config)

    @patch.dict(
        os.environ,
        {
            "EMAIL_SENDER": "test@example.com",
            "EMAIL_PASSWORD": "test-password",
            "EMAIL_RECIPIENT": "recipient@example.com",
        },
    )
    def test_get_email_config(self):
        """Test email configuration retrieval"""
        manager = CredentialsManager(str(self.config_dir))
        config = manager.get_email_config()

        self.assertEqual(config["sender_email"], "test@example.com")
        self.assertEqual(config["sender_password"], "test-password")
        self.assertEqual(config["recipient_email"], "recipient@example.com")
        self.assertEqual(config["smtp_server"], "smtp.test.com")
        self.assertEqual(config["smtp_port"], 587)

    @patch.dict(os.environ, {})
    def test_get_email_config_missing_password(self):
        """Test email configuration with missing password"""
        manager = CredentialsManager(str(self.config_dir))

        with self.assertRaises(ValueError):
            manager.get_email_config()

    @patch.dict(
        os.environ,
        {"OLLAMA_API_KEY": "test-ollama-key", "EMAIL_PASSWORD": "test-email-password"},
    )
    def test_validate_required_credentials_success(self):
        """Test successful credential validation"""
        manager = CredentialsManager(str(self.config_dir))
        self.assertTrue(manager.validate_required_credentials())

    @patch.dict(os.environ, {})
    def test_validate_required_credentials_failure(self):
        """Test failed credential validation"""
        manager = CredentialsManager(str(self.config_dir))
        self.assertFalse(manager.validate_required_credentials())

    @patch.dict(
        os.environ,
        {
            "OLLAMA_API_KEY": "test-ollama-key",
            "EMAIL_PASSWORD": "test-email-password",
            "SERPAPI_KEY": "test-serpapi-key",
            "HUNTER_KEY": "test-hunter-key",
            "APIFY_KEY": "test-apify-key",
            "BRIGHTDATA_PASSWORD": "test-brightdata-password",
        },
    )
    def test_get_all_config(self):
        """Test complete configuration retrieval"""
        manager = CredentialsManager(str(self.config_dir))
        config = manager.get_all_config()

        # Verify all sections are present
        self.assertIn("nvidia", config)
        self.assertIn("serpapi", config)
        self.assertIn("hunter", config)
        self.assertIn("apify", config)
        self.assertIn("brightdata", config)
        self.assertIn("email", config)
        self.assertIn("gmail", config)
        self.assertIn("search", config)
        self.assertIn("quality", config)
        self.assertIn("scheduler", config)
        self.assertIn("monitoring", config)

        # Verify specific values
        self.assertEqual(config["ollama"]["api_key"], "test-ollama-key")
        self.assertEqual(config["serpapi"]["api_key"], "test-serpapi-key")
        self.assertEqual(config["email"]["sender_password"], "test-email-password")


if __name__ == "__main__":
    unittest.main()
