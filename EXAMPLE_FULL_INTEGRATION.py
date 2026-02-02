#!/usr/bin/env python3
"""
Example: Full Integration with Database, Export, and Dashboard
Shows how to use all the new features together
"""

import asyncio
import logging
from pathlib import Path

# Add src to path
import sys
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.credentials_manager import CredentialsManager
from src.database import DatabaseService
from src.export_service import ExportService
from src.llm_service import LLMService
from src.search_service import SearchService
from src.scraping_service import ScrapingService
from src.performance_optimizer import PerformanceOptimizer
from src.signal_processor import SignalProcessor
from src.workflows.lead_generator import LeadGenerator

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


async def main():
    """Full integration example"""
    
    logger.info("🚀 Starting full integration example...")
    
    # 1. Initialize all services
    logger.info("📦 Initializing services...")
    credentials_manager = CredentialsManager()
    llm_service = LLMService(credentials_manager)
    
    import requests
    session = requests.Session()
    config = credentials_manager.get_all_config()
    
    search_service = SearchService(
        session,
        config.get("newsdata", {}).get("api_key"),
        config.get("serpapi", {}).get("api_key"),
    )
    scraping_service = ScrapingService(session)
    performance_optimizer = PerformanceOptimizer(llm_service=llm_service)
    
    signal_processor = SignalProcessor(
        llm_service=llm_service,
        search_service=search_service,
        scraping_service=scraping_service,
        performance_optimizer=performance_optimizer,
    )
    
    # 2. Initialize database and export services
    database_service = DatabaseService(database_url="sqlite:///opportunities.db")
    export_service = ExportService(output_dir="exports")
    
    # 3. Initialize lead generator with database and export
    lead_generator = LeadGenerator(
        signal_processor=signal_processor,
        checkpoint_dir="checkpoints",
        enable_checkpointing=True,
        database_service=database_service,
        export_service=export_service,
    )
    
    # 4. Generate leads (async - much faster!)
    logger.info("🔍 Generating leads...")
    opportunities = await lead_generator.generate_leads_async(
        signal_ids=[1, 2, 3],  # Process signals 1, 2, and 3
        max_opportunities=50,
        max_concurrent=3,  # Process 3 signals in parallel
    )
    
    logger.info(f"✅ Generated {len(opportunities)} opportunities")
    
    # 5. Filter and deduplicate
    logger.info("🔍 Filtering and deduplicating...")
    unique_opportunities = lead_generator.filter_and_deduplicate(
        opportunities,
        similarity_threshold=90,
        use_email_as_key=True,
    )
    
    logger.info(f"✅ {len(unique_opportunities)} unique opportunities after deduplication")
    
    # 6. Get metrics
    metrics = lead_generator.get_quality_metrics()
    stats = lead_generator.get_processing_stats()
    
    logger.info("=" * 60)
    logger.info("📈 QUALITY METRICS")
    logger.info("=" * 60)
    logger.info(f"Total opportunities: {metrics['total_opportunities']}")
    logger.info(f"Average relevance: {metrics['average_relevance_score']:.2f}")
    logger.info(f"High quality (≥0.8): {metrics['high_quality_count']} ({metrics['quality_percentage']}%)")
    logger.info(f"Emails found: {metrics['email_found_count']} ({metrics['email_found_percentage']}%)")
    logger.info(f"Duration: {stats.get('duration_minutes', 0):.2f} minutes")
    
    # 7. Export to Excel with beautiful formatting
    logger.info("📊 Exporting to Excel...")
    excel_path = export_service.export_to_excel(
        unique_opportunities,
        include_content=False,
        apply_formatting=True,
    )
    logger.info(f"✅ Exported to {excel_path}")
    
    # 8. Export summary report
    logger.info("📈 Exporting summary report...")
    report_path = export_service.export_summary_report(
        unique_opportunities,
        metrics,
    )
    logger.info(f"✅ Exported summary report to {report_path}")
    
    # 9. Query from database
    logger.info("💾 Querying from database...")
    db_opportunities = database_service.get_opportunities(
        min_relevance=0.7,
        limit=100,
    )
    logger.info(f"✅ Found {len(db_opportunities)} opportunities in database (relevance ≥ 0.7)")
    
    # 10. Get database statistics
    db_stats = database_service.get_statistics()
    logger.info("=" * 60)
    logger.info("💾 DATABASE STATISTICS")
    logger.info("=" * 60)
    logger.info(f"Total in DB: {db_stats['total_opportunities']}")
    logger.info(f"Average relevance: {db_stats['avg_relevance']:.3f}")
    logger.info(f"Contacted: {db_stats['contacted_count']} ({db_stats['contacted_percentage']}%)")
    
    logger.info("=" * 60)
    logger.info("✅ Full integration example completed!")
    logger.info("=" * 60)
    logger.info("")
    logger.info("📊 To view the dashboard, run:")
    logger.info("   streamlit run dashboard.py")
    logger.info("")
    
    return unique_opportunities


if __name__ == "__main__":
    opportunities = asyncio.run(main())

