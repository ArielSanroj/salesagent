#!/usr/bin/env python3
"""
Tests for outbound.py - Main lead generation system
"""

import pytest
import os
import tempfile
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

# Add src to path for imports
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from outbound import (
    initialize_services, create_session, acquire_lock, release_lock,
    is_valid_url, extract_text_from_html, calculate_relevance_score,
    parse_article_date, is_valid_email, save_results, filter_results,
    send_email_report, main
)
from models import Opportunity


class TestOutboundSystem:
    """Test cases for the main outbound system"""
    
    def test_initialize_services_success(self):
        """Test successful service initialization"""
        with patch('outbound.CredentialsManager') as mock_creds, \
             patch('outbound.LLMService') as mock_llm, \
             patch('outbound.create_session') as mock_session:
            
            # Mock credentials manager
            mock_creds_instance = Mock()
            mock_creds_instance.validate_required_credentials.return_value = True
            mock_creds_instance.get_all_config.return_value = {"test": "config"}
            mock_creds.return_value = mock_creds_instance
            
            # Mock LLM service
            mock_llm_instance = Mock()
            mock_llm.return_value = mock_llm_instance
            
            # Mock session
            mock_session.return_value = Mock()
            
            result = initialize_services()
            assert result is True
    
    def test_initialize_services_failure(self):
        """Test service initialization failure"""
        with patch('outbound.CredentialsManager') as mock_creds:
            mock_creds_instance = Mock()
            mock_creds_instance.validate_required_credentials.return_value = False
            mock_creds.return_value = mock_creds_instance
            
            result = initialize_services()
            assert result is False
    
    def test_create_session(self):
        """Test session creation"""
        session = create_session()
        assert session is not None
        assert hasattr(session, 'mount')
    
    def test_acquire_lock_success(self):
        """Test successful lock acquisition"""
        with patch('os.open') as mock_open, \
             patch('fcntl.flock') as mock_flock, \
             patch('os.write') as mock_write, \
             patch('os.close') as mock_close:
            
            mock_fd = 123
            mock_open.return_value = mock_fd
            mock_flock.return_value = None
            
            result = acquire_lock()
            assert result is True
    
    def test_acquire_lock_failure(self):
        """Test lock acquisition failure"""
        with patch('os.open') as mock_open:
            mock_open.side_effect = OSError("Lock file exists")
            
            result = acquire_lock()
            assert result is False
    
    def test_release_lock(self):
        """Test lock release"""
        with patch('os.path.exists') as mock_exists, \
             patch('os.unlink') as mock_unlink:
            
            mock_exists.return_value = True
            release_lock()
            mock_unlink.assert_called_once()
    
    def test_is_valid_url(self):
        """Test URL validation"""
        assert is_valid_url("https://example.com") is True
        assert is_valid_url("http://example.com") is True
        assert is_valid_url("invalid-url") is False
        assert is_valid_url("") is False
        assert is_valid_url(None) is False
    
    def test_extract_text_from_html(self):
        """Test HTML text extraction"""
        html = "<html><body><h1>Title</h1><p>Content</p></body></html>"
        text = extract_text_from_html(html)
        assert "Title" in text
        assert "Content" in text
        assert "<" not in text  # No HTML tags
    
    def test_calculate_relevance_score(self):
        """Test relevance score calculation"""
        content = "HR tech productivity burnout employee engagement"
        keywords = ["HR tech", "productivity", "burnout", "employee engagement"]
        
        score = calculate_relevance_score(content, keywords)
        assert 0 <= score <= 1
        assert score > 0.5  # Should be high relevance
    
    def test_calculate_relevance_score_no_keywords(self):
        """Test relevance score with no keywords"""
        content = "Some random content"
        keywords = []
        
        score = calculate_relevance_score(content, keywords)
        assert score == 0.0
    
    def test_parse_article_date(self):
        """Test article date parsing"""
        # Valid date
        date_str = "2024-01-15"
        result = parse_article_date(date_str)
        assert result == "2024-01-15"
        
        # Invalid date
        result = parse_article_date("invalid-date")
        assert result is None
        
        # Empty date
        result = parse_article_date("")
        assert result is None
    
    def test_is_valid_email(self):
        """Test email validation"""
        assert is_valid_email("test@example.com") is True
        assert is_valid_email("user.name@domain.co.uk") is True
        assert is_valid_email("invalid-email") is False
        assert is_valid_email("") is False
        assert is_valid_email(None) is False
    
    def test_save_results(self):
        """Test saving results to CSV"""
        opportunities = [
            Opportunity(
                title="Test Title",
                company="Test Company",
                person="Test Person",
                email="test@example.com",
                url="https://example.com",
                date="2024-01-15",
                content="Test content",
                relevance_score=0.8,
                signal_type=1,
                source="Test Source"
            )
        ]
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            temp_file = f.name
        
        try:
            save_results(opportunities, temp_file)
            assert os.path.exists(temp_file)
            
            # Verify CSV content
            with open(temp_file, 'r') as f:
                content = f.read()
                assert "Test Company" in content
                assert "Test Person" in content
        
        finally:
            if os.path.exists(temp_file):
                os.unlink(temp_file)
    
    def test_save_results_empty(self):
        """Test saving empty results"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            temp_file = f.name
        
        try:
            save_results([], temp_file)
            # Should not raise exception
            assert True
        
        finally:
            if os.path.exists(temp_file):
                os.unlink(temp_file)
    
    def test_filter_results(self):
        """Test filtering and deduplicating results"""
        opportunities = [
            Opportunity(
                title="Title 1", company="Company A", person="Person 1",
                email="email1@example.com", url="url1", date="2024-01-15",
                content="Content 1", relevance_score=0.9, signal_type=1, source="Source 1"
            ),
            Opportunity(
                title="Title 2", company="Company A", person="Person 1",  # Duplicate
                email="email1@example.com", url="url2", date="2024-01-15",
                content="Content 2", relevance_score=0.7, signal_type=1, source="Source 2"
            ),
            Opportunity(
                title="Title 3", company="Company B", person="Person 2",
                email="email2@example.com", url="url3", date="2024-01-15",
                content="Content 3", relevance_score=0.8, signal_type=2, source="Source 3"
            )
        ]
        
        filtered = filter_results(opportunities)
        assert len(filtered) == 2  # One duplicate removed
        assert filtered[0].relevance_score >= filtered[1].relevance_score  # Sorted by score
    
    def test_filter_results_empty(self):
        """Test filtering empty results"""
        filtered = filter_results([])
        assert filtered == []
    
    @patch('outbound.CONFIG')
    def test_send_email_report_success(self, mock_config):
        """Test successful email report sending"""
        mock_config.get.return_value = {
            "smtp_server": "smtp.gmail.com",
            "smtp_port": 587,
            "sender_email": "test@example.com",
            "sender_password": "password",
            "recipient_email": "recipient@example.com"
        }
        
        with patch('smtplib.SMTP') as mock_smtp:
            mock_server = Mock()
            mock_smtp.return_value = mock_server
            
            result = send_email_report("Test report content")
            assert result is True
            mock_server.starttls.assert_called_once()
            mock_server.login.assert_called_once()
            mock_server.sendmail.assert_called_once()
            mock_server.quit.assert_called_once()
    
    @patch('outbound.CONFIG')
    def test_send_email_report_failure(self, mock_config):
        """Test email report sending failure"""
        mock_config.get.return_value = None
        
        result = send_email_report("Test report content")
        assert result is False
    
    @patch('outbound.acquire_lock')
    @patch('outbound.initialize_services')
    @patch('outbound.run_signal')
    @patch('outbound.filter_results')
    @patch('outbound.save_results')
    @patch('outbound.send_email_report')
    @patch('outbound.release_lock')
    def test_main_weekly_run(self, mock_release, mock_email, mock_save, mock_filter, 
                            mock_run, mock_init, mock_lock):
        """Test main function with weekly run"""
        # Setup mocks
        mock_lock.return_value = True
        mock_init.return_value = True
        mock_run.return_value = [Mock()]
        mock_filter.return_value = [Mock()]
        mock_save.return_value = None
        mock_email.return_value = True
        
        # Set environment variable
        with patch.dict(os.environ, {'WEEKLY_RUN': 'true'}):
            main()
        
        # Verify calls
        mock_lock.assert_called_once()
        mock_init.assert_called_once()
        mock_release.assert_called_once()
    
    @patch('outbound.acquire_lock')
    @patch('outbound.initialize_services')
    @patch('outbound.test_signal')
    @patch('outbound.release_lock')
    def test_main_test_run(self, mock_release, mock_test, mock_init, mock_lock):
        """Test main function with test run"""
        # Setup mocks
        mock_lock.return_value = True
        mock_init.return_value = True
        mock_test.return_value = [Mock()]
        
        # Set environment variable
        with patch.dict(os.environ, {'WEEKLY_RUN': 'false'}):
            main()
        
        # Verify calls
        mock_lock.assert_called_once()
        mock_init.assert_called_once()
        mock_test.assert_called_once_with(1)
        mock_release.assert_called_once()
    
    def test_main_lock_failure(self):
        """Test main function when lock acquisition fails"""
        with patch('outbound.acquire_lock') as mock_lock:
            mock_lock.return_value = False
            
            with pytest.raises(SystemExit):
                main()


if __name__ == "__main__":
    pytest.main([__file__])
