#!/usr/bin/env python3
"""
Example: How to use the improved async LeadGenerator

This demonstrates the new async capabilities, checkpointing, and improved features.
"""

import asyncio
import logging
from src.credentials_manager import CredentialsManager
from src.llm_service import LLMService
from src.search_service import SearchService
from src.scraping_service import ScrapingService
from src.performance_optimizer import PerformanceOptimizer
from src.signal_processor import SignalProcessor
from src.workflows.lead_generator import LeadGenerator
from src.constants import SIGNAL_TYPES

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


async def main():
    """Example async usage of LeadGenerator"""
    
    # Initialize services
    logger.info("🚀 Initializing services...")
    credentials_manager = CredentialsManager()
    
    # Initialize LLM service
    llm_service = LLMService(credentials_manager)
    
    # Initialize search and scraping services
    import requests
    session = requests.Session()
    config = credentials_manager.get_all_config()
    
    search_service = SearchService(
        session,
        config.get("newsdata", {}).get("api_key"),
        config.get("serpapi", {}).get("api_key"),
    )
    scraping_service = ScrapingService(session)
    
    # Initialize performance optimizer with LLM
    performance_optimizer = PerformanceOptimizer(llm_service=llm_service)
    
    # Initialize signal processor
    signal_processor = SignalProcessor(
        llm_service=llm_service,
        search_service=search_service,
        scraping_service=scraping_service,
        performance_optimizer=performance_optimizer,
    )
    
    # Initialize lead generator with checkpointing enabled
    lead_generator = LeadGenerator(
        signal_processor=signal_processor,
        checkpoint_dir="checkpoints",
        enable_checkpointing=True,
    )
    
    # Option 1: Use async method (RECOMMENDED - much faster!)
    logger.info("📊 Starting async lead generation...")
    opportunities = await lead_generator.generate_leads_async(
        signal_ids=[1, 2, 3],  # Process signals 1, 2, and 3
        max_opportunities=50,
        max_concurrent=3,  # Process 3 signals in parallel
    )
    
    # Filter and deduplicate with fuzzy matching
    logger.info("🔍 Filtering and deduplicating...")
    unique_opportunities = lead_generator.filter_and_deduplicate(
        opportunities,
        similarity_threshold=90,  # 90% similarity threshold
        use_email_as_key=True,  # Use email as primary key when available
    )
    
    # Get comprehensive metrics
    metrics = lead_generator.get_quality_metrics()
    stats = lead_generator.get_processing_stats()
    
    logger.info("=" * 60)
    logger.info("📈 QUALITY METRICS")
    logger.info("=" * 60)
    logger.info(f"Total opportunities: {metrics['total_opportunities']}")
    logger.info(f"Average relevance: {metrics['average_relevance_score']:.2f}")
    logger.info(f"High quality (≥0.8): {metrics['high_quality_count']} ({metrics['quality_percentage']}%)")
    logger.info(f"Emails found: {metrics['email_found_count']} ({metrics['email_found_percentage']}%)")
    logger.info(f"Recent (30 days): {metrics['recent_opportunities']} ({metrics['recent_percentage']}%)")
    
    logger.info("\n📊 DISTRIBUTION BY SIGNAL:")
    for signal_name, data in metrics['success_rate_by_signal'].items():
        logger.info(f"  {signal_name}: {data['count']} opportunities ({data['percentage']}%)")
    
    logger.info("\n🎯 QUALITY TIERS:")
    for tier, count in metrics['quality_tiers'].items():
        logger.info(f"  {tier.capitalize()}: {count}")
    
    logger.info("\n⏱️  PERFORMANCE STATS:")
    logger.info(f"  Duration: {stats.get('duration_minutes', 0):.2f} minutes")
    logger.info(f"  Signals processed: {stats['signals_processed']}")
    logger.info(f"  Errors: {stats['errors']}")
    
    # Option 2: Load from checkpoint if needed
    # checkpoint_opps = lead_generator.load_checkpoint("checkpoints/checkpoint_opportunities_20250101_120000.json")
    
    logger.info("=" * 60)
    logger.info(f"✅ Generated {len(unique_opportunities)} unique opportunities")
    logger.info("=" * 60)
    
    return unique_opportunities


def main_sync():
    """Example synchronous usage (backward compatible but slower)"""
    
    # ... same initialization ...
    
    # Use sync method (slower, but backward compatible)
    opportunities = lead_generator.generate_leads(
        signal_ids=[1, 2, 3],
        max_opportunities=50,
    )
    
    return opportunities


if __name__ == "__main__":
    # Run async version
    opportunities = asyncio.run(main())
    
    # You can also use the sync version for backward compatibility
    # opportunities = main_sync()

