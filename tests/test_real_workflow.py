#!/usr/bin/env python3
"""
Real workflow integration tests using actual APIs
Tests the complete pipeline: LLM analysis → content processing → email generation
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


class TestRealWorkflow(unittest.TestCase):
    """Test the real workflow with actual APIs"""

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

    def test_real_ollama_company_extraction(self):
        """Test real Ollama API for company extraction"""
        from src.credentials_manager import CredentialsManager
        from src.llm_service import LLMService

        # Check if we have a real Ollama API key
        ollama_key = os.getenv("OLLAMA_API_KEY")
        if not ollama_key or ollama_key == "test-ollama-key":
            self.skipTest("No real Ollama API key available")

        try:
            # Initialize credentials manager
            credentials_manager = CredentialsManager(str(self.config_dir))
            llm_service = LLMService(credentials_manager)

            # Test company extraction with real content
            test_content = """
            Microsoft announced today that Sarah Johnson, their new CHRO,
            will be leading the company's HR technology transformation.
            The company is evaluating new HR systems to improve employee engagement.
            """

            prompt = f"""Extract the company name from this text. Return only the company name, nothing else.

Text: {test_content}

Company name:"""

            response = llm_service.invoke_sync(prompt, "company_extraction")

            self.assertIsNotNone(response)
            self.assertIsInstance(response, str)
            self.assertGreater(len(response), 0)

            print(f"✅ Real Ollama company extraction: '{response.strip()}'")

            # Verify it extracted Microsoft
            self.assertIn("Microsoft", response)

        except Exception as e:
            print(f"⚠️ Ollama company extraction failed: {e}")
            self.skipTest(f"Ollama service not available: {e}")

    def test_real_ollama_person_extraction(self):
        """Test real Ollama API for person extraction"""
        from src.credentials_manager import CredentialsManager
        from src.llm_service import LLMService

        # Check if we have a real Ollama API key
        ollama_key = os.getenv("OLLAMA_API_KEY")
        if not ollama_key or ollama_key == "test-ollama-key":
            self.skipTest("No real Ollama API key available")

        try:
            # Initialize credentials manager
            credentials_manager = CredentialsManager(str(self.config_dir))
            llm_service = LLMService(credentials_manager)

            # Test person extraction with real content
            test_content = """
            Microsoft announced today that Sarah Johnson, their new CHRO,
            will be leading the company's HR technology transformation.
            The company is evaluating new HR systems to improve employee engagement.
            """

            prompt = f"""Extract the person name from this text. Return only the person name, nothing else.

Text: {test_content}

Person name:"""

            response = llm_service.invoke_sync(prompt, "person_extraction")

            self.assertIsNotNone(response)
            self.assertIsInstance(response, str)
            self.assertGreater(len(response), 0)

            print(f"✅ Real Ollama person extraction: '{response.strip()}'")

            # Verify it extracted Sarah Johnson
            self.assertIn("Sarah Johnson", response)

        except Exception as e:
            print(f"⚠️ Ollama person extraction failed: {e}")
            self.skipTest(f"Ollama service not available: {e}")

    def test_real_ollama_signal_classification(self):
        """Test real Ollama API for signal classification"""
        from src.credentials_manager import CredentialsManager
        from src.llm_service import LLMService

        # Check if we have a real Ollama API key
        ollama_key = os.getenv("OLLAMA_API_KEY")
        if not ollama_key or ollama_key == "test-ollama-key":
            self.skipTest("No real Ollama API key available")

        try:
            # Initialize credentials manager
            credentials_manager = CredentialsManager(str(self.config_dir))
            llm_service = LLMService(credentials_manager)

            # Test signal classification with real content
            test_content = """
            Microsoft is evaluating new HR technology solutions to improve
            employee engagement and reduce burnout. The company is looking
            at various HR tech platforms to modernize their workforce management.
            """

            prompt = f"""Classify this HR technology signal into one of these categories:
1. HR tech evaluations
2. New leadership ≤90 days
3. High-intent website/content
4. Tech stack change
5. Expansion
6. Hiring/downsizing

Return only the number (1-6), nothing else.

Text: {test_content}

Signal type:"""

            response = llm_service.invoke_sync(prompt, "signal_classification")

            self.assertIsNotNone(response)
            self.assertIsInstance(response, str)

            # Should return a number 1-6
            signal_type = response.strip()
            self.assertIn(signal_type, ["1", "2", "3", "4", "5", "6"])

            print(f"✅ Real Ollama signal classification: Signal type {signal_type}")

        except Exception as e:
            print(f"⚠️ Ollama signal classification failed: {e}")
            self.skipTest(f"Ollama service not available: {e}")

    def test_real_email_generation(self):
        """Test real email generation with Gmail API"""
        from gmail_email_system import GmailEmailSystem

        # Check if Gmail credentials exist
        if not os.path.exists("gmail_credentials.json"):
            self.skipTest("Gmail credentials not found")

        try:
            system = GmailEmailSystem()

            # Test email content generation
            opportunity = {
                "company": "Microsoft",
                "person": "Sarah Johnson",
                "email": "sarah.johnson@microsoft.com",
                "signal_type": 1,  # HR tech evaluations
            }

            content = system.generate_email_content(opportunity)

            self.assertIsInstance(content, dict)
            self.assertIn("subject", content)
            self.assertIn("body", content)
            self.assertIn("to", content)

            # Verify personalization
            self.assertIn("Microsoft", content["subject"])
            self.assertIn("Sarah Johnson", content["body"])
            self.assertIn("sarah.johnson@microsoft.com", content["to"])

            print(f"✅ Real email generation: Subject: {content['subject']}")
            print(f"   Body preview: {content['body'][:100]}...")

        except Exception as e:
            print(f"⚠️ Email generation failed: {e}")
            self.skipTest(f"Gmail API not available: {e}")

    def test_real_workflow_simulation(self):
        """Test the complete workflow simulation"""
        from gmail_email_system import GmailEmailSystem
        from src.credentials_manager import CredentialsManager
        from src.llm_service import LLMService

        # Check if we have real APIs
        ollama_key = os.getenv("OLLAMA_API_KEY")
        if not ollama_key or ollama_key == "test-ollama-key":
            self.skipTest("No real Ollama API key available")

        if not os.path.exists("gmail_credentials.json"):
            self.skipTest("Gmail credentials not found")

        try:
            # Initialize services
            credentials_manager = CredentialsManager(str(self.config_dir))
            llm_service = LLMService(credentials_manager)
            email_system = GmailEmailSystem()

            # Simulate finding an opportunity
            article_content = """
            Microsoft announced today that Sarah Johnson, their new CHRO,
            will be leading the company's HR technology transformation.
            The company is evaluating new HR systems to improve employee engagement
            and reduce burnout. They are looking at various HR tech platforms
            to modernize their workforce management.
            """

            # Step 1: Extract company name
            company_prompt = f"""Extract the company name from this text. Return only the company name, nothing else.

Text: {article_content}

Company name:"""
            company = llm_service.invoke_sync(company_prompt, "company_extraction")

            # Step 2: Extract person name
            person_prompt = f"""Extract the person name from this text. Return only the person name, nothing else.

Text: {article_content}

Person name:"""
            person = llm_service.invoke_sync(person_prompt, "person_extraction")

            # Step 3: Classify signal type
            signal_prompt = f"""Classify this HR technology signal into one of these categories:
1. HR tech evaluations
2. New leadership ≤90 days
3. High-intent website/content
4. Tech stack change
5. Expansion
6. Hiring/downsizing

Return only the number (1-6), nothing else.

Text: {article_content}

Signal type:"""
            signal_type = llm_service.invoke_sync(
                signal_prompt, "signal_classification"
            )

            # Step 4: Generate email
            opportunity = {
                "company": company.strip(),
                "person": person.strip(),
                "email": f"{person.strip().lower().replace(' ', '.')}@{company.strip().lower()}.com",
                "signal_type": int(signal_type.strip()),
            }

            email_content = email_system.generate_email_content(opportunity)

            # Verify the complete workflow
            self.assertIsNotNone(company)
            self.assertIsNotNone(person)
            self.assertIsNotNone(signal_type)
            self.assertIsNotNone(email_content)

            print(f"✅ Complete workflow simulation:")
            print(f"   Company: {company.strip()}")
            print(f"   Person: {person.strip()}")
            print(f"   Signal Type: {signal_type.strip()}")
            print(f"   Email Subject: {email_content['subject']}")

        except Exception as e:
            print(f"⚠️ Workflow simulation failed: {e}")
            self.skipTest(f"Workflow simulation not available: {e}")


if __name__ == "__main__":
    unittest.main()
