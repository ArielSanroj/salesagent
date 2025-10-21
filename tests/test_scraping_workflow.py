#!/usr/bin/env python3
"""
Unit tests for Scraping Workflow
"""

import os
import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


class TestScrapingWorkflow(unittest.TestCase):
    """Test cases for scraping workflow components"""

    def setUp(self):
        """Set up test fixtures"""
        self.mock_credentials = Mock()
        self.mock_llm_service = Mock()

    def test_url_validation(self):
        """Test URL validation logic"""
        from outbound import is_valid_url

        # Valid URLs
        self.assertTrue(is_valid_url("https://example.com"))
        self.assertTrue(is_valid_url("http://example.com"))
        self.assertTrue(is_valid_url("https://www.example.com/path"))

        # Invalid URLs
        self.assertFalse(is_valid_url("not-a-url"))
        self.assertFalse(is_valid_url("ftp://example.com"))
        self.assertFalse(is_valid_url(""))
        self.assertFalse(is_valid_url(None))

    def test_content_extraction(self):
        """Test content extraction from HTML"""
        from outbound import extract_text_from_html

        html_content = """
        <html>
            <head><title>Test Article</title></head>
            <body>
                <h1>Main Title</h1>
                <p>This is the main content about HR technology.</p>
                <div class="sidebar">Sidebar content</div>
            </body>
        </html>
        """

        text = extract_text_from_html(html_content)

        self.assertIn("Test Article", text)
        self.assertIn("Main Title", text)
        self.assertIn("main content about HR technology", text)
        self.assertNotIn("Sidebar content", text)  # Should be filtered out

    def test_relevance_scoring(self):
        """Test relevance scoring logic"""
        from outbound import calculate_relevance_score

        # High relevance content
        content = "HR technology solutions for employee engagement and productivity"
        keywords = ["HR tech", "employee engagement", "productivity"]
        score = calculate_relevance_score(content, keywords)

        self.assertGreater(score, 0.7)

        # Low relevance content
        content = "Random content about cooking recipes"
        score = calculate_relevance_score(content, keywords)

        self.assertLess(score, 0.3)

    def test_company_extraction(self):
        """Test company name extraction"""
        from outbound import extract_company_name

        # Test cases
        test_cases = [
            ("John Smith from Microsoft", "Microsoft"),
            ("Jane Doe at Google Inc.", "Google"),
            ("HR Director at Apple", "Apple"),
            ("No company mentioned", None),
            ("", None),
        ]

        for text, expected in test_cases:
            result = extract_company_name(text)
            self.assertEqual(result, expected)

    def test_person_extraction(self):
        """Test person name extraction"""
        from outbound import extract_person_name

        # Test cases
        test_cases = [
            ("John Smith from Microsoft", "John Smith"),
            ("Jane Doe, HR Director", "Jane Doe"),
            ("CEO Sarah Johnson", "Sarah Johnson"),
            ("No person mentioned", None),
            ("", None),
        ]

        for text, expected in test_cases:
            result = extract_person_name(text)
            self.assertEqual(result, expected)

    def test_date_parsing(self):
        """Test date parsing functionality"""
        from outbound import parse_article_date

        # Test cases
        test_cases = [
            ("2025-01-15", "2025-01-15"),
            ("January 15, 2025", "2025-01-15"),
            ("15/01/2025", "2025-01-15"),
            ("Invalid date", None),
            ("", None),
        ]

        for date_str, expected in test_cases:
            result = parse_article_date(date_str)
            self.assertEqual(result, expected)

    def test_email_validation(self):
        """Test email validation logic"""
        from outbound import is_valid_email

        # Valid emails
        self.assertTrue(is_valid_email("john.doe@example.com"))
        self.assertTrue(is_valid_email("jane@company.org"))
        self.assertTrue(is_valid_email("test+tag@domain.co.uk"))

        # Invalid emails
        self.assertFalse(is_valid_email("not-an-email"))
        self.assertFalse(is_valid_email("john@"))
        self.assertFalse(is_valid_email("@company.com"))
        self.assertFalse(is_valid_email(""))
        self.assertFalse(is_valid_email(None))

    def test_signal_classification(self):
        """Test signal type classification"""
        from outbound import classify_signal_type

        # Test cases for different signal types
        test_cases = [
            ("evaluating HR technology solutions", 1),  # HR Tech Evaluations
            ("new CHRO appointed", 2),  # New Leadership
            ("HR tech content on website", 3),  # High-Intent Content
            ("switching HR systems", 4),  # Tech Stack Change
            ("company expansion and growth", 5),  # Expansion
            ("hiring new HR team members", 6),  # Hiring/Downsizing
            ("unrelated content", None),  # No signal
        ]

        for content, expected in test_cases:
            result = classify_signal_type(content)
            self.assertEqual(result, expected)

    def test_data_quality_validation(self):
        """Test data quality validation"""
        from outbound import validate_opportunity_data

        # Valid opportunity data
        valid_data = {
            "title": "Test Article",
            "company": "Test Company",
            "person": "John Doe",
            "email": "john@test.com",
            "relevance_score": 0.8,
            "signal_type": 1,
        }

        self.assertTrue(validate_opportunity_data(valid_data))

        # Invalid opportunity data
        invalid_data = {
            "title": "",  # Empty title
            "company": "Test Company",
            "person": "John Doe",
            "email": "invalid-email",  # Invalid email
            "relevance_score": 0.3,  # Low relevance
            "signal_type": 1,
        }

        self.assertFalse(validate_opportunity_data(invalid_data))

    def test_csv_export(self):
        """Test CSV export functionality"""
        from outbound import export_to_csv

        # Test data
        data = [
            {
                "title": "Test Article 1",
                "company": "Company 1",
                "person": "Person 1",
                "email": "person1@company1.com",
                "relevance_score": 0.8,
                "signal_type": 1,
            },
            {
                "title": "Test Article 2",
                "company": "Company 2",
                "person": "Person 2",
                "email": "person2@company2.com",
                "relevance_score": 0.9,
                "signal_type": 2,
            },
        ]

        # Test CSV export
        csv_content = export_to_csv(data)

        self.assertIn("Test Article 1", csv_content)
        self.assertIn("Company 1", csv_content)
        self.assertIn("person1@company1.com", csv_content)
        self.assertIn("Test Article 2", csv_content)
        self.assertIn("Company 2", csv_content)
        self.assertIn("person2@company2.com", csv_content)


if __name__ == "__main__":
    unittest.main()
