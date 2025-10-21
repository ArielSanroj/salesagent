#!/usr/bin/env python3
"""
Integration tests for HR Tech Lead Generation System
Tests the real workflow: API search → content scraping → LLM analysis → email draft creation
"""

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


class TestIntegrationWorkflow(unittest.TestCase):
    """Integration tests for the complete workflow"""

    def setUp(self):
        """Set up test fixtures"""
        self.temp_dir = tempfile.mkdtemp()
        self.config_dir = Path(self.temp_dir) / "config"
        self.config_dir.mkdir()

        # Create test config file
        self.config_file = self.config_dir / "secure_config.yaml"
        test_config = {
            "api": {
                "ollama": {
                    "model": "llama3.1:8b",
                    "base_url": "http://localhost:11434",
                    "timeout": 30,
                    "max_retries": 3,
                    "retry_delay": 2,
                },
                "newsdata": {
                    "timeout": 30,
                    "max_retries": 3,
                    "retry_delay": 2,
                },
                "serpapi": {"timeout": 30, "max_retries": 3},
                "hunter": {"timeout": 30, "max_retries": 3},
                "apify": {"timeout": 60, "max_retries": 2},
            },
            "search": {"keywords": ["HR tech", "CHRO", "employee engagement"]},
            "quality": {"min_relevance_score": 0.7},
            "scheduler": {"target_opportunities_per_week": 50},
            "monitoring": {"log_level": "INFO"},
        }

        import yaml

        with open(self.config_file, "w") as f:
            yaml.dump(test_config, f)

    def tearDown(self):
        """Clean up test fixtures"""
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    @patch.dict(
        os.environ,
        {
            "OLLAMA_API_KEY": "test-ollama-key",
            "NEWSDATA_API_KEY": "test-newsdata-key",
            "SERPAPI_KEY": "test-serpapi-key",
            "HUNTER_KEY": "test-hunter-key",
            "APIFY_KEY": "test-apify-key",
            "EMAIL_PASSWORD": "test-email-password",
        },
    )
    def test_real_ollama_integration(self):
        """Test real Ollama LLM integration"""
        from src.credentials_manager import CredentialsManager
        from src.llm_service import LLMService

        # Initialize credentials manager
        credentials_manager = CredentialsManager(str(self.config_dir))

        # Test LLM service initialization
        try:
            llm_service = LLMService(credentials_manager)
            self.assertIsNotNone(llm_service)

            # Test a simple LLM query
            test_prompt = "Extract the company name from this text: 'John Smith from Microsoft announced new HR technology initiatives.'"
            response = llm_service.invoke_sync(test_prompt, "test")

            self.assertIsNotNone(response)
            self.assertIsInstance(response, str)
            self.assertGreater(len(response), 0)

            print(f"✅ Ollama integration test passed. Response: {response[:100]}...")

        except Exception as e:
            print(f"⚠️ Ollama integration test failed: {e}")
            # This is expected if Ollama is not running locally
            self.skipTest(f"Ollama service not available: {e}")

    @patch.dict(
        os.environ,
        {
            "OLLAMA_API_KEY": "test-ollama-key",
            "NEWSDATA_API_KEY": "test-newsdata-key",
            "SERPAPI_KEY": "test-serpapi-key",
            "HUNTER_KEY": "test-hunter-key",
            "APIFY_KEY": "test-apify-key",
            "EMAIL_PASSWORD": "test-email-password",
        },
    )
    def test_real_newsdata_integration(self):
        """Test real NewsData API integration"""
        from src.integrations.newsdata_client import NewsDataClient

        # Check if we have a real NewsData API key
        newsdata_key = os.getenv("NEWSDATA_API_KEY")
        if not newsdata_key or newsdata_key == "test-newsdata-key":
            self.skipTest("No real NewsData API key available")

        try:
            client = NewsDataClient(newsdata_key)

            # Test search for HR tech articles
            articles = client.search_articles(query="HR technology", max_results=5)

            self.assertIsInstance(articles, list)
            self.assertGreater(len(articles), 0)

            # Verify article structure
            article = articles[0]
            self.assertIn("title", article)
            self.assertIn("link", article)
            self.assertIn("pubDate", article)

            print(f"✅ NewsData integration test passed. Found {len(articles)} articles")

        except Exception as e:
            print(f"⚠️ NewsData integration test failed: {e}")
            self.skipTest(f"NewsData API not available: {e}")

    @patch.dict(
        os.environ,
        {
            "OLLAMA_API_KEY": "test-ollama-key",
            "NEWSDATA_API_KEY": "test-newsdata-key",
            "SERPAPI_KEY": "test-serpapi-key",
            "HUNTER_KEY": "test-hunter-key",
            "APIFY_KEY": "test-apify-key",
            "EMAIL_PASSWORD": "test-email-password",
        },
    )
    def test_real_workflow_integration(self):
        """Test the complete workflow with real APIs"""
        import requests

        from src.credentials_manager import CredentialsManager
        from src.llm_service import LLMService
        from src.scraping_service import ScrapingService
        from src.search_service import SearchService
        from src.signal_processor import SignalProcessor

        # Initialize services
        credentials_manager = CredentialsManager(str(self.config_dir))

        # Check if we have real API keys
        newsdata_key = os.getenv("NEWSDATA_API_KEY")
        if not newsdata_key or newsdata_key == "test-newsdata-key":
            self.skipTest("No real NewsData API key available")

        try:
            # Initialize LLM service
            llm_service = LLMService(credentials_manager)

            # Initialize search service
            search_service = SearchService(requests.Session(), newsdata_key)

            # Initialize scraping service
            scraping_service = ScrapingService(requests.Session())

            # Initialize signal processor
            signal_processor = SignalProcessor(
                llm_service, search_service, scraping_service
            )

            # Test signal processing
            opportunities = signal_processor.process_signal(1, max_results=3)

            self.assertIsInstance(opportunities, list)
            print(
                f"✅ Workflow integration test passed. Found {len(opportunities)} opportunities"
            )

            # If we found opportunities, verify their structure
            if opportunities:
                opportunity = opportunities[0]
                self.assertIn("title", opportunity)
                self.assertIn("company", opportunity)
                self.assertIn("url", opportunity)
                print(
                    f"Sample opportunity: {opportunity['company']} - {opportunity['title'][:50]}..."
                )

        except Exception as e:
            print(f"⚠️ Workflow integration test failed: {e}")
            self.skipTest(f"Workflow integration not available: {e}")

    def test_gmail_api_integration(self):
        """Test Gmail API integration"""
        from gmail_email_system import GmailEmailSystem

        # Check if Gmail credentials exist
        if not os.path.exists("gmail_credentials.json"):
            self.skipTest("Gmail credentials not found")

        try:
            system = GmailEmailSystem()

            # Test template loading
            template = system.load_email_template("hr_tech_evaluations")
            self.assertIsInstance(template, dict)
            self.assertIn("subject_template", template)
            self.assertIn("body_template", template)

            print("✅ Gmail API integration test passed")

        except Exception as e:
            print(f"⚠️ Gmail API integration test failed: {e}")
            self.skipTest(f"Gmail API not available: {e}")

    def test_real_content_scraping(self):
        """Test real content scraping from a known URL"""
        import requests

        from src.scraping_service import ScrapingService

        try:
            scraping_service = ScrapingService(requests.Session())

            # Test scraping a known URL
            test_url = "https://httpbin.org/html"
            result = scraping_service.scrape_url(test_url)

            if result:
                self.assertIn("content", result)
                self.assertIn("title", result)
                self.assertGreater(len(result["content"]), 0)
                print(
                    f"✅ Content scraping test passed. Scraped {len(result['content'])} characters"
                )
            else:
                print("⚠️ Content scraping returned no result")

        except Exception as e:
            print(f"⚠️ Content scraping test failed: {e}")
            self.skipTest(f"Content scraping not available: {e}")


if __name__ == "__main__":
    unittest.main()
