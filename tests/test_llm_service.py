#!/usr/bin/env python3
"""
Unit tests for LLM Service
"""

import os
import sys
import time
import unittest
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from credentials_manager import CredentialsManager
from src.llm_service import LLMResponse, LLMService, LLMStatus


class TestLLMService(unittest.TestCase):
    """Test cases for LLM Service"""

    def setUp(self):
        """Set up test fixtures"""
        # Mock credentials manager
        self.mock_credentials = Mock(spec=CredentialsManager)
        self.mock_credentials.get_ollama_config.return_value = {
            "model": "test-model",
            "api_key": "test-key",
            "base_url": "https://test.api.com/v1",
            "max_retries": 3,
            "retry_delay": 1,
            "timeout": 30,
        }

        # Create LLM service with mocked credentials
        self.llm_service = LLMService(self.mock_credentials)

    def tearDown(self):
        """Clean up after tests"""
        self.llm_service.stop_worker_thread()

    @patch("langchain_ollama.ChatOllama")
    def test_initialization_success(self, mock_chat_ollama):
        """Test successful LLM service initialization"""
        # Mock successful LLM client
        mock_client = Mock()
        mock_response = Mock()
        mock_response.content = "Test response"
        mock_client.invoke.return_value = mock_response
        mock_chat_ollama.return_value = mock_client

        # Create new service
        service = LLMService(self.mock_credentials)

        # Verify initialization
        self.assertEqual(service.status, LLMStatus.HEALTHY)
        self.assertEqual(service.retry_count, 0)

    @patch("langchain_ollama.ChatOllama")
    def test_initialization_failure(self, mock_chat_ollama):
        """Test LLM service initialization failure"""
        # Mock failing LLM client
        mock_chat_ollama.side_effect = Exception("Connection failed")

        # Create service - should not raise exception
        service = LLMService(self.mock_credentials)

        # Verify degraded state
        self.assertEqual(service.status, LLMStatus.FAILED)

    def test_fallback_response(self):
        """Test fallback response generation"""
        request = {"prompt": "Test prompt", "type": "email_finder"}

        response = self.llm_service._get_fallback_response(request)

        self.assertIsInstance(response, LLMResponse)
        self.assertFalse(response.success)
        self.assertTrue(response.fallback_used)
        self.assertEqual(response.content, "Manual validation needed")

    def test_health_check_healthy(self):
        """Test health check when service is healthy"""
        self.llm_service.status = LLMStatus.HEALTHY
        self.assertTrue(self.llm_service.health_check())

    def test_health_check_failed(self):
        """Test health check when service is failed"""
        self.llm_service.status = LLMStatus.FAILED
        self.assertFalse(self.llm_service.health_check())

    def test_get_status(self):
        """Test status reporting"""
        status = self.llm_service.get_status()

        self.assertIn("status", status)
        self.assertIn("retry_count", status)
        self.assertIn("queue_size", status)
        self.assertIn("worker_alive", status)

    def test_fallback_responses(self):
        """Test fallback response content"""
        fallbacks = self.llm_service.fallback_responses

        self.assertIn("email_finder", fallbacks)
        self.assertIn("content_parser", fallbacks)
        self.assertIn("relevance_scorer", fallbacks)

        self.assertEqual(fallbacks["email_finder"], "Manual validation needed")
        self.assertEqual(
            fallbacks["content_parser"],
            "Content parsing failed - manual review required",
        )


class TestLLMResponse(unittest.TestCase):
    """Test cases for LLMResponse dataclass"""

    def test_successful_response(self):
        """Test successful response creation"""
        response = LLMResponse(content="Test content", success=True, retry_count=0)

        self.assertEqual(response.content, "Test content")
        self.assertTrue(response.success)
        self.assertIsNone(response.error)
        self.assertEqual(response.retry_count, 0)
        self.assertFalse(response.fallback_used)

    def test_failed_response(self):
        """Test failed response creation"""
        response = LLMResponse(
            content="Fallback content",
            success=False,
            error="Service unavailable",
            retry_count=3,
            fallback_used=True,
        )

        self.assertEqual(response.content, "Fallback content")
        self.assertFalse(response.success)
        self.assertEqual(response.error, "Service unavailable")
        self.assertEqual(response.retry_count, 3)
        self.assertTrue(response.fallback_used)


if __name__ == "__main__":
    unittest.main()
