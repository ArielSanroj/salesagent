#!/usr/bin/env python3
"""
HR Tech Lead Generation System - Main Orchestrator
Coordinates signal processing, data enrichment, and reporting
"""

import logging
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import List

from dotenv import load_dotenv

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent / "src"))

from constants import SIGNAL_TYPES, LOCK_FILE
from credentials_manager import CredentialsManager
from email_service import send_email_report, summarize_opportunities
from http_utils import create_session
from llm_service import LLMService
from models import Opportunity
from performance_optimizer import PerformanceOptimizer
from process_lock import acquire_lock, release_lock
from results_manager import filter_results, save_results, get_timestamped_filename
from scraping_service import ScrapingService
from search_service import SearchService
from signal_processor_refactored import SignalProcessor

# Load environment variables
load_dotenv()

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    filename="scrape.log",
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


class LeadGenerationSystem:
    """Main orchestrator for lead generation"""

    def __init__(self):
        self.credentials_manager = None
        self.llm_service = None
        self.gmail_system = None
        self.config = None
        self.session = None

    def initialize(self) -> bool:
        """Initialize all services with secure configuration"""
        try:
            self.credentials_manager = CredentialsManager()

            if not self.credentials_manager.validate_required_credentials():
                logger.error("Missing required credentials")
                return False

            self.config = self.credentials_manager.get_all_config()

            try:
                self.llm_service = LLMService(self.credentials_manager)
                logger.info("LLM service initialized successfully")
            except Exception as e:
                logger.warning(f"LLM service initialization failed: {e}")
                self.llm_service = None

            self.session = create_session()

            logger.info("All services initialized successfully")
            return True

        except Exception as e:
            logger.error(f"Failed to initialize services: {e}")
            return False

    def run_signal(self, signal_id: int) -> List[Opportunity]:
        """Run a specific signal type"""
        logger.info(f"Running signal {signal_id}: {SIGNAL_TYPES.get(signal_id, 'Unknown')}")

        # Initialize services
        newsdata_config = self.config.get("newsdata") or {}
        serpapi_config = self.config.get("serpapi") or {}

        search_service = SearchService(
            self.session,
            newsdata_config.get("api_key"),
            serpapi_config.get("api_key"),
        )
        scraping_service = ScrapingService(self.session)

        performance_optimizer = PerformanceOptimizer(llm_service=self.llm_service)

        signal_processor = SignalProcessor(
            self.llm_service,
            search_service,
            scraping_service,
            performance_optimizer,
            self.config.get("quality", {}),
        )

        opportunities = signal_processor.process_signal(signal_id, 10)

        logger.info(f"Signal {signal_id} completed: {len(opportunities)} opportunities")
        return opportunities

    def run_full_lead_generation(self, target_opportunities: int) -> List[Opportunity]:
        """Run all signals and return filtered opportunities"""
        logger.info("Starting full lead generation workflow")
        all_opportunities = []

        for signal_id in range(1, 7):
            opportunities = self.run_signal(signal_id)
            all_opportunities.extend(opportunities)

            if target_opportunities and len(all_opportunities) >= target_opportunities:
                logger.info(f"Collected {len(all_opportunities)} raw opportunities")

            time.sleep(5)

        filtered = filter_results(all_opportunities)
        if target_opportunities > 0:
            filtered = filtered[:target_opportunities]

        # Save results
        timestamp_file = get_timestamped_filename("all_signals")
        save_results(filtered, timestamp_file)
        save_results(filtered, "all_signals.csv")

        # Create email drafts
        self._create_email_drafts(filtered)

        logger.info(f"Lead generation completed with {len(filtered)} opportunities")
        return filtered

    def _create_email_drafts(self, opportunities: List[Opportunity]) -> None:
        """Create Gmail drafts for the provided opportunities"""
        if not opportunities:
            logger.info("No opportunities for email draft creation")
            return

        if self.gmail_system is None:
            try:
                from gmail_email_system import GmailEmailSystem
                self.gmail_system = GmailEmailSystem(self.credentials_manager)
                logger.info("Gmail email system initialized")
            except Exception as e:
                logger.error(f"Unable to initialize Gmail email system: {e}")
                return

        payload = [
            {
                "company": opp.company,
                "person": opp.person,
                "email": opp.email,
                "signal_type": opp.signal_type,
                "url": opp.url,
            }
            for opp in opportunities
        ]

        try:
            drafts = self.gmail_system.create_batch_drafts(payload) or []
            self.gmail_system.save_draft_summary(drafts)
            logger.info("Email drafts created and summarized")
        except Exception as e:
            logger.error(f"Error creating Gmail drafts: {e}")

    def send_report(
        self,
        opportunities: List[Opportunity],
        target: int,
        is_weekly: bool = False
    ) -> bool:
        """Send email report"""
        email_config = self.config.get("email", {})
        if not email_config:
            logger.error("Email configuration not found")
            return False

        subject = (
            f"Weekly HR Tech Lead Generation Report - {datetime.now().strftime('%Y-%m-%d')}"
            if is_weekly
            else "daily leads"
        )

        report_content = summarize_opportunities(opportunities, target)

        return send_email_report(
            email_config,
            report_content,
            "all_signals.csv",
            subject,
            opportunities
        )

    def cleanup(self) -> None:
        """Cleanup resources"""
        if self.llm_service:
            self.llm_service.stop_worker_thread()


def test_signal(signal_id: int) -> List[Opportunity]:
    """Test a single signal for development"""
    logger.info(f"Testing signal {signal_id}")

    system = LeadGenerationSystem()
    if not system.initialize():
        logger.error("Failed to initialize")
        return []

    try:
        opportunities = system.run_signal(signal_id)
        if opportunities:
            filename = get_timestamped_filename(f"test_signal_{signal_id}")
            save_results(opportunities, filename)
            logger.info(f"Test completed: {len(opportunities)} opportunities saved")
        else:
            logger.warning(f"No opportunities found for signal {signal_id}")
        return opportunities
    finally:
        system.cleanup()


def main() -> None:
    """Main execution function"""
    if not acquire_lock(LOCK_FILE):
        sys.exit(1)

    system = LeadGenerationSystem()

    try:
        if not system.initialize():
            logger.error("Failed to initialize services")
            sys.exit(1)

        is_weekly_run = os.getenv("WEEKLY_RUN", "false").lower() == "true"
        target = int(os.getenv("TARGET_OPPORTUNITIES", "50"))
        run_label = "weekly" if is_weekly_run else "daily"

        logger.info(f"Starting {run_label} run - Target: {target} opportunities")

        filtered = system.run_full_lead_generation(target)

        # Send email if not skipped
        skip_email = os.getenv("SKIP_EMAIL", "false").lower() == "true"

        if filtered and not skip_email:
            system.send_report(filtered, target, is_weekly_run)
        elif filtered and skip_email:
            logger.info("Skipping email send (handled by scheduler)")
        else:
            logger.warning("No opportunities generated during this run")

    except Exception as e:
        logger.error(f"Workflow failed: {e}", exc_info=True)
    finally:
        system.cleanup()
        release_lock(LOCK_FILE)


if __name__ == "__main__":
    main()
