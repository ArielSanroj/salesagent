#!/usr/bin/env python3
"""
Secure Credentials Manager for HR Tech Lead Generation System
Handles all API keys and sensitive configuration securely
"""

import logging
import os
from pathlib import Path
from typing import Any, Dict, Optional

import yaml
from dotenv import load_dotenv


class CredentialsManager:
    """Secure manager for API keys and sensitive configuration"""

    def __init__(self, config_dir: str = "config"):
        self.config_dir = Path(config_dir)
        self.logger = logging.getLogger(__name__)

        # Load environment variables
        load_dotenv()

        # Load secure configuration
        self.secure_config = self._load_secure_config()

    def _load_secure_config(self) -> Dict[str, Any]:
        """Load secure configuration from YAML file"""
        config_file = self.config_dir / "secure_config.yaml"

        try:
            with open(config_file, "r") as f:
                return yaml.safe_load(f)
        except FileNotFoundError:
            self.logger.error(f"Configuration file not found: {config_file}")
            raise
        except yaml.YAMLError as e:
            self.logger.error(f"Error parsing configuration file: {e}")
            raise

    def get_ollama_config(self) -> Dict[str, Any]:
        """Get Ollama API configuration with credentials"""
        api_key = os.getenv("OLLAMA_API_KEY")
        if not api_key:
            raise ValueError("OLLAMA_API_KEY environment variable not set")

        config = self.secure_config["api"]["ollama"].copy()
        config["api_key"] = api_key
        return config

    def get_nvidia_config(self) -> Dict[str, Any]:
        """Get NVIDIA AI configuration with credentials"""
        api_key = os.getenv("NVIDIA_API_KEY")
        if not api_key:
            raise ValueError("NVIDIA_API_KEY environment variable not set")

        config = self.secure_config["api"]["nvidia"].copy()
        config["api_key"] = api_key
        return config

    def get_serpapi_config(self) -> Dict[str, Any]:
        """Get SerpAPI configuration with credentials"""
        api_key = os.getenv("SERPAPI_KEY")
        if not api_key:
            self.logger.warning("SERPAPI_KEY not set, SerpAPI features will be disabled")
            return None

        config = self.secure_config["api"]["serpapi"].copy()
        config["api_key"] = api_key
        return config

    def get_hunter_config(self) -> Dict[str, Any]:
        """Get Hunter.io configuration with credentials"""
        api_key = os.getenv("HUNTER_KEY")
        if not api_key:
            self.logger.warning("HUNTER_KEY not set, Hunter.io features will be disabled")
            return None

        config = self.secure_config["api"]["hunter"].copy()
        config["api_key"] = api_key
        return config

    def get_apify_config(self) -> Dict[str, Any]:
        """Get Apify configuration with credentials"""
        api_key = os.getenv("APIFY_KEY")
        if not api_key:
            self.logger.warning("APIFY_KEY not set, Apify features will be disabled")
            return None

        config = self.secure_config["api"]["apify"].copy()
        config["api_key"] = api_key
        return config

    def get_google_sheets_config(self) -> Dict[str, Any]:
        """Get Google Sheets configuration with credentials"""
        api_key = os.getenv("GOOGLE_SHEETS_API_KEY")
        if not api_key:
            self.logger.warning("GOOGLE_SHEETS_API_KEY not set, Google Sheets features will be disabled")
            return None

        config = self.secure_config["api"]["google_sheets"].copy()
        config["api_key"] = api_key
        return config

    def get_google_sheets_settings(self) -> Dict[str, Any]:
        """Get Google Sheets settings (spreadsheet ID, sheet names, etc.)"""
        spreadsheet_id = os.getenv("GOOGLE_SHEETS_ID")
        if not spreadsheet_id:
            self.logger.warning("GOOGLE_SHEETS_ID not set, using default configuration")
            spreadsheet_id = self.secure_config["google_sheets"]["spreadsheet_id"]

        settings = self.secure_config["google_sheets"].copy()
        settings["spreadsheet_id"] = spreadsheet_id
        return settings

    def get_brightdata_config(self) -> Dict[str, Any]:
        """Get BrightData proxy configuration with credentials"""
        password = os.getenv("BRIGHTDATA_PASSWORD")
        if not password:
            self.logger.warning("BRIGHTDATA_PASSWORD not set, proxy features will be disabled")
            return None

        return {
            "username": "brd-customer-hl_0133b0f7-zone-residential_proxy1",
            "password": password,
            "host": "brd.superproxy.io",
            "port": 33335,
            "timeout": 30,
        }

    def get_email_config(self) -> Dict[str, Any]:
        """Get email configuration with credentials"""
        sender_email = os.getenv("EMAIL_SENDER", "ariel@cliocircle.com")
        sender_password = os.getenv("EMAIL_PASSWORD")
        recipient_email = os.getenv("EMAIL_RECIPIENT", "ariel@cliocircle.com")

        if not sender_password:
            raise ValueError("EMAIL_PASSWORD environment variable not set")

        return {
            "smtp_server": self.secure_config["email_config"]["smtp_server"],
            "smtp_port": self.secure_config["email_config"]["smtp_port"],
            "sender_email": sender_email,
            "sender_password": sender_password,
            "recipient_email": recipient_email,
        }

    def get_gmail_config(self) -> Dict[str, Any]:
        """Get Gmail API configuration"""
        credentials_file = os.getenv("GMAIL_CREDENTIALS_FILE", "gmail_credentials.json")
        token_file = os.getenv("GMAIL_TOKEN_FILE", "gmail_token.json")

        if not os.path.exists(credentials_file):
            raise FileNotFoundError(f"Gmail credentials file not found: {credentials_file}")

        return {
            "credentials_file": credentials_file,
            "token_file": token_file,
            "scopes": ["https://www.googleapis.com/auth/gmail.compose"],
        }

    def get_search_config(self) -> Dict[str, Any]:
        """Get search configuration"""
        return self.secure_config["search"]

    def get_quality_config(self) -> Dict[str, Any]:
        """Get quality thresholds configuration"""
        return self.secure_config["quality"]

    def get_scheduler_config(self) -> Dict[str, Any]:
        """Get scheduler configuration"""
        return self.secure_config["scheduler"]

    def get_monitoring_config(self) -> Dict[str, Any]:
        """Get monitoring configuration"""
        return self.secure_config["monitoring"]

    def validate_required_credentials(self) -> bool:
        """Validate that all required credentials are present"""
        required_vars = ["OLLAMA_API_KEY", "EMAIL_PASSWORD"]
        missing_vars = []

        for var in required_vars:
            if not os.getenv(var):
                missing_vars.append(var)

        if missing_vars:
            self.logger.error(f"Missing required environment variables: {missing_vars}")
            return False

        return True

    def get_all_config(self) -> Dict[str, Any]:
        """Get complete configuration with all credentials"""
        if not self.validate_required_credentials():
            raise ValueError("Missing required credentials")

        return {
            "ollama": self.get_ollama_config(),
            "serpapi": self.get_serpapi_config(),
            "hunter": self.get_hunter_config(),
            "apify": self.get_apify_config(),
            "brightdata": self.get_brightdata_config(),
            "email": self.get_email_config(),
            "gmail": self.get_gmail_config(),
            "search": self.get_search_config(),
            "quality": self.get_quality_config(),
            "scheduler": self.get_scheduler_config(),
            "monitoring": self.get_monitoring_config(),
        }
