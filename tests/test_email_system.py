#!/usr/bin/env python3
"""
Unit tests for Email System
"""

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


class TestEmailSystem(unittest.TestCase):
    """Test cases for Email System"""

    def setUp(self):
        """Set up test fixtures"""
        self.mock_credentials = Mock()
        self.mock_llm_service = Mock()

        # Create temporary directory for test files
        self.temp_dir = tempfile.mkdtemp()
        self.test_credentials_file = os.path.join(
            self.temp_dir, "test_credentials.json"
        )
        self.test_token_file = os.path.join(self.temp_dir, "test_token.json")

    def tearDown(self):
        """Clean up after tests"""
        import shutil

        shutil.rmtree(self.temp_dir)

    def test_email_template_loading(self):
        """Test email template loading from YAML"""
        from gmail_email_system import GmailEmailSystem

        # Mock the template loading
        with patch("yaml.safe_load") as mock_yaml:
            mock_yaml.return_value = {
                "templates": {
                    "hr_tech_evaluations": {
                        "subject_template": "Test Subject - {company_name}",
                        "opening_template": "Hi {person_name},",
                        "body_template": "Test body content",
                        "closing_template": "Best regards, Ariel",
                    }
                }
            }

            system = GmailEmailSystem()
            template = system.load_email_template("hr_tech_evaluations")

            self.assertIsNotNone(template)
            self.assertIn("subject_template", template)
            self.assertIn("opening_template", template)

    def test_email_personalization(self):
        """Test email personalization with variables"""
        from gmail_email_system import GmailEmailSystem

        system = GmailEmailSystem()

        # Test data
        template = {
            "subject_template": "Hello {person_name} from {company_name}",
            "opening_template": "Hi {person_name},",
            "body_template": "This is about {company_name}",
            "closing_template": "Best regards, {sender_name}",
        }

        variables = {
            "person_name": "John Doe",
            "company_name": "Test Company",
            "sender_name": "Ariel",
        }

        personalized = system.personalize_template(template, variables)

        self.assertEqual(personalized["subject"], "Hello John Doe from Test Company")
        self.assertEqual(personalized["opening"], "Hi John Doe,")
        self.assertEqual(personalized["body"], "This is about Test Company")
        self.assertEqual(personalized["closing"], "Best regards, Ariel")

    def test_email_validation(self):
        """Test email address validation"""
        from gmail_email_system import GmailEmailSystem

        system = GmailEmailSystem()

        # Valid emails
        self.assertTrue(system.is_valid_email("john.doe@example.com"))
        self.assertTrue(system.is_valid_email("jane@company.org"))
        self.assertTrue(system.is_valid_email("test+tag@domain.co.uk"))

        # Invalid emails
        self.assertFalse(system.is_valid_email("not-an-email"))
        self.assertFalse(system.is_valid_email("john@"))
        self.assertFalse(system.is_valid_email("@company.com"))
        self.assertFalse(system.is_valid_email(""))
        self.assertFalse(system.is_valid_email(None))

    def test_draft_creation(self):
        """Test Gmail draft creation"""
        from gmail_email_system import GmailEmailSystem

        system = GmailEmailSystem()

        # Mock Gmail service
        mock_service = Mock()
        mock_drafts = Mock()
        mock_drafts.create.return_value = {"id": "test-draft-id"}
        mock_service.drafts.return_value = mock_drafts

        system.service = mock_service

        # Test draft creation
        draft_data = {
            "to": "test@example.com",
            "subject": "Test Subject",
            "body": "Test body content",
        }

        result = system.create_draft(draft_data)

        self.assertIsNotNone(result)
        self.assertEqual(result["id"], "test-draft-id")
        mock_drafts.create.assert_called_once()

    def test_signal_type_mapping(self):
        """Test signal type to template mapping"""
        from gmail_email_system import GmailEmailSystem

        system = GmailEmailSystem()

        # Test signal type mapping
        test_cases = [
            (1, "hr_tech_evaluations"),
            (2, "new_leadership"),
            (3, "high_intent_content"),
            (4, "tech_stack_change"),
            (5, "expansion"),
            (6, "hiring_downsizing"),
        ]

        for signal_type, expected_template in test_cases:
            template_name = system.get_template_for_signal(signal_type)
            self.assertEqual(template_name, expected_template)

    def test_email_content_generation(self):
        """Test complete email content generation"""
        from gmail_email_system import GmailEmailSystem

        system = GmailEmailSystem()

        # Mock template loading
        with patch.object(system, "load_email_template") as mock_load:
            mock_load.return_value = {
                "subject_template": "Test Subject - {company_name}",
                "opening_template": "Hi {person_name},",
                "body_template": "This is about {company_name}",
                "closing_template": "Best regards, {sender_name}",
            }

            # Test data
            opportunity = {
                "company": "Test Company",
                "person": "John Doe",
                "email": "john@test.com",
                "signal_type": 1,
            }

            content = system.generate_email_content(opportunity)

            self.assertIn("Test Company", content["subject"])
            self.assertIn("John Doe", content["opening"])
            self.assertIn("Test Company", content["body"])
            self.assertIn("Ariel", content["closing"])

    def test_batch_draft_creation(self):
        """Test batch creation of email drafts"""
        from gmail_email_system import GmailEmailSystem

        system = GmailEmailSystem()

        # Mock Gmail service
        mock_service = Mock()
        mock_drafts = Mock()
        mock_drafts.create.return_value = {"id": "test-draft-id"}
        mock_service.drafts.return_value = mock_drafts

        system.service = mock_service

        # Mock template loading
        with patch.object(system, "load_email_template") as mock_load:
            mock_load.return_value = {
                "subject_template": "Test Subject - {company_name}",
                "opening_template": "Hi {person_name},",
                "body_template": "This is about {company_name}",
                "closing_template": "Best regards, {sender_name}",
            }

            # Test data
            opportunities = [
                {
                    "company": "Company 1",
                    "person": "Person 1",
                    "email": "person1@company1.com",
                    "signal_type": 1,
                },
                {
                    "company": "Company 2",
                    "person": "Person 2",
                    "email": "person2@company2.com",
                    "signal_type": 2,
                },
            ]

            results = system.create_batch_drafts(opportunities)

            self.assertEqual(len(results), 2)
            self.assertEqual(mock_drafts.create.call_count, 2)

    def test_error_handling(self):
        """Test error handling in email operations"""
        from gmail_email_system import GmailEmailSystem

        system = GmailEmailSystem()

        # Mock Gmail service that raises exception
        mock_service = Mock()
        mock_drafts = Mock()
        mock_drafts.create.side_effect = Exception("Gmail API error")
        mock_service.drafts.return_value = mock_drafts

        system.service = mock_service

        # Test error handling
        draft_data = {
            "to": "test@example.com",
            "subject": "Test Subject",
            "body": "Test body content",
        }

        result = system.create_draft(draft_data)

        self.assertIsNone(result)

    def test_template_validation(self):
        """Test email template validation"""
        from gmail_email_system import GmailEmailSystem

        system = GmailEmailSystem()

        # Valid template
        valid_template = {
            "subject_template": "Test Subject - {company_name}",
            "opening_template": "Hi {person_name},",
            "body_template": "This is about {company_name}",
            "closing_template": "Best regards, {sender_name}",
        }

        self.assertTrue(system.validate_template(valid_template))

        # Invalid template (missing required fields)
        invalid_template = {
            "subject_template": "Test Subject - {company_name}",
            # Missing other required fields
        }

        self.assertFalse(system.validate_template(invalid_template))


if __name__ == "__main__":
    unittest.main()
