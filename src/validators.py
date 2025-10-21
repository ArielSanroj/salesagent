#!/usr/bin/env python3
"""
Validators for HR Tech Lead Generation System
Input validation and sanitization utilities
"""

import re
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

from exceptions import ValidationError


class InputValidator:
    """Input validation utilities"""

    @staticmethod
    def is_valid_email(email: str) -> bool:
        """Validate email format"""
        if not email or not isinstance(email, str):
            return False

        pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
        return bool(re.match(pattern, email))

    @staticmethod
    def is_valid_url(url: str) -> bool:
        """Validate URL format"""
        if not url or not isinstance(url, str):
            return False

        try:
            result = urlparse(url)
            return all([result.scheme, result.netloc]) and result.scheme in [
                "http",
                "https",
            ]
        except Exception:
            return False

    @staticmethod
    def validate_signal_type(signal_type: int) -> bool:
        """Validate signal type is between 1-6"""
        return 1 <= signal_type <= 6

    @staticmethod
    def validate_relevance_score(score: float) -> bool:
        """Validate relevance score is between 0-1"""
        return 0.0 <= score <= 1.0

    @staticmethod
    def sanitize_text(text: str, max_length: int = 1000) -> str:
        """Sanitize text input"""
        if not text:
            return ""

        # Remove HTML tags
        text = re.sub(r"<[^>]+>", "", text)

        # Remove extra whitespace
        text = re.sub(r"\s+", " ", text).strip()

        # Truncate if too long
        if len(text) > max_length:
            text = text[:max_length] + "..."

        return text

    @staticmethod
    def validate_opportunity_data(data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate and sanitize opportunity data"""
        required_fields = ["title", "company", "url"]

        for field in required_fields:
            if not data.get(field):
                raise ValidationError(f"Missing required field: {field}")

        # Sanitize text fields
        text_fields = ["title", "company", "person", "content"]
        for field in text_fields:
            if field in data:
                data[field] = InputValidator.sanitize_text(data[field])

        # Validate email
        if "email" in data and data["email"]:
            if not InputValidator.is_valid_email(data["email"]):
                data["email"] = "Manual validation needed"

        # Validate URL
        if not InputValidator.is_valid_url(data["url"]):
            raise ValidationError(f"Invalid URL: {data['url']}")

        # Validate signal type
        if "signal_type" in data:
            if not InputValidator.validate_signal_type(data["signal_type"]):
                raise ValidationError(f"Invalid signal type: {data['signal_type']}")

        # Validate relevance score
        if "relevance_score" in data:
            if not InputValidator.validate_relevance_score(data["relevance_score"]):
                raise ValidationError(
                    f"Invalid relevance score: {data['relevance_score']}"
                )

        return data


class ConfigValidator:
    """Configuration validation utilities"""

    @staticmethod
    def validate_required_env_vars() -> List[str]:
        """Validate required environment variables are set"""
        required_vars = [
            "OLLAMA_API_KEY",
            "EMAIL_PASSWORD",
            "EMAIL_SENDER",
            "EMAIL_RECIPIENT",
        ]

        missing_vars = []
        import os

        for var in required_vars:
            if not os.getenv(var):
                missing_vars.append(var)

        return missing_vars

    @staticmethod
    def validate_api_keys(config: Dict[str, Any]) -> List[str]:
        """Validate API keys are present in configuration"""
        missing_keys = []

        api_services = ["newsdata", "hunter", "google_sheets"]
        for service in api_services:
            if service in config and not config[service].get("api_key"):
                missing_keys.append(f"{service}_api_key")

        return missing_keys
