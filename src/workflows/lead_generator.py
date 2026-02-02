#!/usr/bin/env python3
"""
Lead Generator Workflow for HR Tech Lead Generation System
Main workflow orchestration for lead generation process
"""

import asyncio
import logging
from asyncio import Semaphore
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

try:
    from tenacity import retry, stop_after_attempt, wait_exponential
except ImportError:
    retry = lambda *args, **kwargs: lambda func: func
    stop_after_attempt = None
    wait_exponential = None

from ..constants import SIGNAL_TYPES, TARGET_OPPORTUNITIES_PER_WEEK
from ..exceptions import HRTechLeadGenerationError
from ..models import Opportunity
from .checkpoint_manager import CheckpointManager
from .quality_analyzer import QualityAnalyzer

logger = logging.getLogger(__name__)


class LeadGenerator:
    """Main lead generation workflow orchestrator"""

    def __init__(
        self,
        signal_processor,
        checkpoint_dir: str = "checkpoints",
        enable_checkpointing: bool = True,
        database_service=None,
        export_service=None,
    ):
        self.signal_processor = signal_processor
        self.generated_opportunities = []
        self.checkpoint_manager = CheckpointManager(checkpoint_dir)
        self.enable_checkpointing = enable_checkpointing
        self.quality_analyzer = QualityAnalyzer(SIGNAL_TYPES)
        self.database_service = database_service
        self.export_service = export_service
        self.processing_stats = self._init_stats()

    def _init_stats(self) -> Dict[str, Any]:
        """Initialize processing stats"""
        return {
            "start_time": None,
            "end_time": None,
            "total_opportunities": 0,
            "signals_processed": 0,
            "errors": 0,
        }

    def reset(self) -> None:
        """Reset the generator state for reuse"""
        self.generated_opportunities = []
        self.processing_stats = self._init_stats()
        logger.info("LeadGenerator reset for new run")

    def save_checkpoint(self, filename: str = None) -> str:
        """Save current progress to checkpoint"""
        if not self.enable_checkpointing:
            return ""
        return self.checkpoint_manager.save_checkpoint(
            self.generated_opportunities,
            self.processing_stats,
            filename
        )

    def load_checkpoint(self, checkpoint_path: str) -> List[Opportunity]:
        """Load opportunities from checkpoint"""
        data = self.checkpoint_manager.load_checkpoint(checkpoint_path)
        return [self._dict_to_opportunity(d) for d in data]

    def _dict_to_opportunity(self, data: Dict[str, Any]) -> Opportunity:
        """Convert dictionary to Opportunity"""
        return Opportunity(
            title=data.get("title", ""),
            company=data.get("company", ""),
            person=data.get("person", ""),
            email=data.get("email", ""),
            url=data.get("url", ""),
            date=data.get("date", ""),
            content=data.get("content", ""),
            relevance_score=float(data.get("relevance_score", 0.0)),
            signal_type=int(data.get("signal_type", 1)),
            source=data.get("source", ""),
        )

    async def generate_leads_async(
        self,
        signal_ids: List[int] = None,
        max_opportunities: int = TARGET_OPPORTUNITIES_PER_WEEK,
        max_concurrent: int = 5,
    ) -> List[Opportunity]:
        """Generate leads asynchronously with parallel processing"""
        self.processing_stats["start_time"] = datetime.now(timezone.utc)
        self.generated_opportunities = []

        if signal_ids is None:
            signal_ids = list(SIGNAL_TYPES.keys())

        logger.info(f"Starting async lead generation for signals: {signal_ids}")
        logger.info(f"Target opportunities: {max_opportunities}")

        semaphore = Semaphore(max_concurrent)

        async def process_signal(signal_id: int) -> List[Opportunity]:
            async with semaphore:
                return await self._process_one_signal(signal_id, max_opportunities)

        try:
            tasks = [process_signal(sid) for sid in signal_ids]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            self._collect_results(results, signal_ids, max_opportunities)
            self._finalize_processing()

            logger.info(f"Lead generation completed: {len(self.generated_opportunities)} opportunities")
            return self.generated_opportunities

        except Exception as e:
            logger.error(f"Lead generation failed: {e}", exc_info=True)
            raise HRTechLeadGenerationError(f"Lead generation failed: {e}")

    async def _process_one_signal(
        self, signal_id: int, max_opportunities: int
    ) -> List[Opportunity]:
        """Process a single signal"""
        if len(self.generated_opportunities) >= max_opportunities:
            logger.info(f"Target reached, skipping signal {signal_id}")
            return []

        signal_name = SIGNAL_TYPES.get(signal_id, "Unknown")
        logger.info(f"Processing signal {signal_id}: {signal_name}")

        try:
            if hasattr(self.signal_processor, "process_signal_async"):
                opportunities = await self.signal_processor.process_signal_async(signal_id, 10)
            else:
                loop = asyncio.get_event_loop()
                opportunities = await loop.run_in_executor(
                    None, self.signal_processor.process_signal, signal_id, 10
                )

            logger.info(f"Signal {signal_id} completed: {len(opportunities)} opportunities")
            return opportunities

        except Exception as e:
            logger.error(f"Error processing signal {signal_id}: {e}")
            self.processing_stats["errors"] += 1
            return []

    def _collect_results(
        self, results: List, signal_ids: List[int], max_opportunities: int
    ) -> None:
        """Collect results from async processing"""
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Signal {signal_ids[i]} raised exception: {result}")
                self.processing_stats["errors"] += 1
                continue

            if isinstance(result, list):
                self.generated_opportunities.extend(result)
                self.processing_stats["signals_processed"] += 1

                if self.enable_checkpointing:
                    self.save_checkpoint()

                if len(self.generated_opportunities) >= max_opportunities:
                    self.generated_opportunities = self.generated_opportunities[:max_opportunities]
                    logger.info(f"Target reached: {len(self.generated_opportunities)} opportunities")
                    break

    def _finalize_processing(self) -> None:
        """Finalize processing and save to database"""
        self.processing_stats["end_time"] = datetime.now(timezone.utc)
        self.processing_stats["total_opportunities"] = len(self.generated_opportunities)

        if self.database_service:
            try:
                saved = self.database_service.save_opportunities(self.generated_opportunities)
                logger.info(f"Saved {saved} opportunities to database")
            except Exception as e:
                logger.error(f"Error saving to database: {e}")

    def generate_leads(
        self,
        signal_ids: List[int] = None,
        max_opportunities: int = TARGET_OPPORTUNITIES_PER_WEEK,
    ) -> List[Opportunity]:
        """Generate leads synchronously (backward compatibility)"""
        logger.warning("Using synchronous generate_leads. Consider generate_leads_async.")
        return asyncio.run(
            self.generate_leads_async(signal_ids, max_opportunities, max_concurrent=1)
        )

    def filter_and_deduplicate(
        self,
        opportunities: List[Opportunity],
        similarity_threshold: int = 90,
        use_email_as_key: bool = True,
    ) -> List[Opportunity]:
        """Filter and deduplicate opportunities"""
        return self.quality_analyzer.filter_and_deduplicate(
            opportunities, similarity_threshold, use_email_as_key
        )

    def get_processing_stats(self) -> Dict[str, Any]:
        """Get processing statistics"""
        stats = self.processing_stats.copy()

        if stats["start_time"] and stats["end_time"]:
            start = stats["start_time"]
            end = stats["end_time"]

            if isinstance(start, str):
                start = datetime.fromisoformat(start.replace("Z", "+00:00"))
            if isinstance(end, str):
                end = datetime.fromisoformat(end.replace("Z", "+00:00"))

            duration = (end - start).total_seconds()
            stats["duration_seconds"] = round(duration, 2)
            stats["duration_minutes"] = round(duration / 60, 2)

        return stats

    def get_opportunities_by_signal(self) -> Dict[int, List[Opportunity]]:
        """Group opportunities by signal type"""
        by_signal = {}
        for opp in self.generated_opportunities:
            signal = opp.signal_type
            if signal not in by_signal:
                by_signal[signal] = []
            by_signal[signal].append(opp)
        return by_signal

    def get_quality_metrics(self) -> Dict[str, Any]:
        """Get quality metrics for generated opportunities"""
        return self.quality_analyzer.get_quality_metrics(self.generated_opportunities)
