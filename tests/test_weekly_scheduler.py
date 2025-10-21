#!/usr/bin/env python3
"""
Tests for weekly_scheduler.py - Weekly scheduler system
"""

import json
import os

# Add src to path for imports
import sys
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from weekly_scheduler import (
    WeeklyLeadGenerator,
    acquire_scheduler_lock,
    release_scheduler_lock,
)


class TestWeeklyScheduler:
    """Test cases for the weekly scheduler system"""

    def test_acquire_scheduler_lock_success(self):
        """Test successful scheduler lock acquisition"""
        with patch("os.open") as mock_open, patch("fcntl.flock") as mock_flock, patch(
            "os.write"
        ) as mock_write, patch("os.close") as mock_close:
            mock_fd = 123
            mock_open.return_value = mock_fd
            mock_flock.return_value = None

            result = acquire_scheduler_lock()
            assert result is True

    def test_acquire_scheduler_lock_failure(self):
        """Test scheduler lock acquisition failure"""
        with patch("os.open") as mock_open:
            mock_open.side_effect = OSError("Lock file exists")

            result = acquire_scheduler_lock()
            assert result is False

    def test_release_scheduler_lock(self):
        """Test scheduler lock release"""
        with patch("os.path.exists") as mock_exists, patch("os.unlink") as mock_unlink:
            mock_exists.return_value = True
            release_scheduler_lock()
            mock_unlink.assert_called_once()

    def test_weekly_lead_generator_init(self):
        """Test WeeklyLeadGenerator initialization"""
        with patch(
            "weekly_scheduler.CONFIG", {"opportunity_tracking_file": "test.json"}
        ):
            generator = WeeklyLeadGenerator()
            assert generator.opportunities_tracking is not None
            assert "weekly_runs" in generator.opportunities_tracking

    def test_load_tracking_data_existing_file(self):
        """Test loading tracking data from existing file"""
        test_data = {
            "weekly_runs": {"2024-01": {"total_opportunities": 50}},
            "total_opportunities": 50,
            "opportunities_by_week": {"2024-01": 50},
            "last_run": "2024-01-15T10:00:00",
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(test_data, f)
            temp_file = f.name

        try:
            with patch(
                "weekly_scheduler.CONFIG", {"opportunity_tracking_file": temp_file}
            ):
                generator = WeeklyLeadGenerator()
                assert generator.opportunities_tracking == test_data

        finally:
            if os.path.exists(temp_file):
                os.unlink(temp_file)

    def test_load_tracking_data_missing_file(self):
        """Test loading tracking data when file doesn't exist"""
        with patch(
            "weekly_scheduler.CONFIG", {"opportunity_tracking_file": "nonexistent.json"}
        ):
            generator = WeeklyLeadGenerator()
            assert generator.opportunities_tracking["weekly_runs"] == {}
            assert generator.opportunities_tracking["total_opportunities"] == 0

    def test_save_tracking_data(self):
        """Test saving tracking data"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            temp_file = f.name

        try:
            with patch(
                "weekly_scheduler.CONFIG", {"opportunity_tracking_file": temp_file}
            ):
                generator = WeeklyLeadGenerator()
                generator.opportunities_tracking["test_key"] = "test_value"
                generator.save_tracking_data()

                # Verify file was created and contains data
                assert os.path.exists(temp_file)
                with open(temp_file, "r") as f:
                    data = json.load(f)
                    assert data["test_key"] == "test_value"

        finally:
            if os.path.exists(temp_file):
                os.unlink(temp_file)

    def test_cleanup_old_data(self):
        """Test cleanup of old data"""
        with patch(
            "weekly_scheduler.CONFIG",
            {"data_retention_days": 7, "opportunity_tracking_file": "test.json"},
        ):
            generator = WeeklyLeadGenerator()

            # Clear any existing data that might have wrong format
            generator.opportunities_tracking["opportunities_by_week"] = {}

            # Add old data
            old_date = datetime.now() - timedelta(days=10)
            # Use ISO format that can be parsed by fromisoformat
            old_date_str = old_date.isoformat()
            generator.opportunities_tracking["opportunities_by_week"][old_date_str] = 10

            # Test that the method runs without error
            generator.cleanup_old_data()

            # Verify old data was removed
            assert (
                old_date_str
                not in generator.opportunities_tracking["opportunities_by_week"]
            )

    @patch("weekly_scheduler.subprocess.run")
    def test_run_lead_generation_success(self, mock_run):
        """Test successful lead generation run"""
        mock_run.return_value = Mock(returncode=0, stderr="")

        with patch(
            "weekly_scheduler.CONFIG",
            {
                "opportunity_tracking_file": "test.json",
                "target_opportunities_per_week": 50,
            },
        ):
            generator = WeeklyLeadGenerator()

            with patch.object(generator, "process_results") as mock_process:
                result = generator.run_lead_generation()
                assert result is True
                mock_process.assert_called_once()

    @patch("weekly_scheduler.subprocess.run")
    def test_run_lead_generation_failure(self, mock_run):
        """Test failed lead generation run"""
        mock_run.return_value = Mock(returncode=1, stderr="Error occurred")

        with patch(
            "weekly_scheduler.CONFIG", {"opportunity_tracking_file": "test.json"}
        ):
            generator = WeeklyLeadGenerator()

            result = generator.run_lead_generation()
            assert result is False

    @patch("weekly_scheduler.subprocess.run")
    def test_run_lead_generation_timeout(self, mock_run):
        """Test lead generation timeout"""
        import subprocess

        mock_run.side_effect = subprocess.TimeoutExpired("python", 3600)

        with patch(
            "weekly_scheduler.CONFIG", {"opportunity_tracking_file": "test.json"}
        ):
            generator = WeeklyLeadGenerator()

            result = generator.run_lead_generation()
            assert result is False

    @patch("pandas.read_csv")
    def test_process_results(self, mock_read_csv):
        """Test processing results from CSV"""
        # Mock DataFrame
        mock_df = Mock()
        mock_df.__len__ = Mock(return_value=25)
        # Mock the DataFrame indexing and value_counts
        mock_series = Mock()
        mock_series.value_counts.return_value.to_dict.return_value = {
            1: 10,
            2: 15,
        }
        mock_df.__getitem__ = Mock(return_value=mock_series)
        mock_read_csv.return_value = mock_df

        with patch(
            "weekly_scheduler.CONFIG",
            {
                "opportunity_tracking_file": "test.json",
                "target_opportunities_per_week": 50,
            },
        ):
            generator = WeeklyLeadGenerator()
            # Reset the tracking data to ensure clean state
            generator.opportunities_tracking["total_opportunities"] = 0

            with patch("os.path.exists") as mock_exists:
                # Mock that only all_signals.csv exists, not individual signal files
                def exists_side_effect(path):
                    return path == "all_signals.csv"

                mock_exists.side_effect = exists_side_effect

                generator.process_results()

                # Verify tracking data was updated
                assert generator.opportunities_tracking["total_opportunities"] == 25
                assert len(generator.opportunities_tracking["weekly_runs"]) > 0

    @patch("smtplib.SMTP")
    def test_send_weekly_report_success(self, mock_smtp):
        """Test successful weekly report sending"""
        mock_server = Mock()
        mock_smtp.return_value = mock_server

        with patch(
            "weekly_scheduler.CONFIG",
            {
                "opportunity_tracking_file": "test.json",
                "email_recipient": "test@example.com",
                "target_opportunities_per_week": 50,
            },
        ):
            generator = WeeklyLeadGenerator()
            generator.opportunities_tracking["weekly_runs"]["2024-01"] = {
                "total_opportunities": 50,
                "target_met": True,
                "signal_counts": {1: 25, 2: 25},
            }

            with patch.object(
                generator.credentials_manager, "get_email_config"
            ) as mock_email_config:
                mock_email_config.return_value = {
                    "smtp_server": "smtp.gmail.com",
                    "smtp_port": 587,
                    "sender_email": "sender@example.com",
                    "sender_password": "password",
                }

                generator.send_weekly_report()
                mock_server.starttls.assert_called_once()
                mock_server.login.assert_called_once()
                mock_server.sendmail.assert_called_once()
                mock_server.quit.assert_called_once()

    @patch("smtplib.SMTP")
    def test_send_weekly_report_failure(self, mock_smtp):
        """Test weekly report sending failure"""
        mock_smtp.side_effect = Exception("SMTP error")

        with patch(
            "weekly_scheduler.CONFIG",
            {
                "opportunity_tracking_file": "test.json",
                "email_recipient": "test@example.com",
            },
        ):
            generator = WeeklyLeadGenerator()

            # Should not raise exception
            generator.send_weekly_report()

    def test_run_weekly_job_success(self):
        """Test successful weekly job execution"""
        with patch(
            "weekly_scheduler.CONFIG",
            {"opportunity_tracking_file": "test.json", "data_retention_days": 90},
        ):
            generator = WeeklyLeadGenerator()

            with patch.object(
                generator, "cleanup_old_data"
            ) as mock_cleanup, patch.object(
                generator, "run_lead_generation", return_value=True
            ) as mock_run, patch.object(
                generator, "send_weekly_report"
            ) as mock_send:
                generator.run_weekly_job()

                mock_cleanup.assert_called_once()
                mock_run.assert_called_once()
                mock_send.assert_called_once()

    def test_run_weekly_job_failure(self):
        """Test weekly job execution failure"""
        with patch(
            "weekly_scheduler.CONFIG",
            {"opportunity_tracking_file": "test.json", "data_retention_days": 90},
        ):
            generator = WeeklyLeadGenerator()

            with patch.object(
                generator, "cleanup_old_data"
            ) as mock_cleanup, patch.object(
                generator, "run_lead_generation", return_value=False
            ) as mock_run, patch.object(
                generator, "send_weekly_report"
            ) as mock_send:
                generator.run_weekly_job()

                mock_cleanup.assert_called_once()
                mock_run.assert_called_once()
                mock_send.assert_not_called()  # Should not send report on failure


if __name__ == "__main__":
    pytest.main([__file__])
