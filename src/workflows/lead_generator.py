#!/usr/bin/env python3
"""
Lead Generator Workflow for HR Tech Lead Generation System
Main workflow orchestration for lead generation process
"""

import logging
import time
from datetime import datetime
from typing import Any, Dict, List, Optional

from ..constants import SIGNAL_TYPES, TARGET_OPPORTUNITIES_PER_WEEK
from ..exceptions import HRTechLeadGenerationError
from ..models import Opportunity
from .signal_processor import SignalProcessor

logger = logging.getLogger(__name__)


class LeadGenerator:
    """Main lead generation workflow orchestrator"""

    def __init__(self, signal_processor: SignalProcessor):
        self.signal_processor = signal_processor
        self.generated_opportunities = []
        self.processing_stats = {
            "start_time": None,
            "end_time": None,
            "total_opportunities": 0,
            "signals_processed": 0,
            "errors": 0,
        }

    def generate_leads(
        self,
        signal_ids: Optional[List[int]] = None,
        max_opportunities: int = TARGET_OPPORTUNITIES_PER_WEEK,
    ) -> List[Opportunity]:
        """Generate leads for specified signal types"""
        self.processing_stats["start_time"] = datetime.now()
        self.generated_opportunities = []

        if signal_ids is None:
            signal_ids = list(SIGNAL_TYPES.keys())

        logger.info(f"Starting lead generation for signals: {signal_ids}")
        logger.info(f"Target opportunities: {max_opportunities}")

        try:
            for signal_id in signal_ids:
                if len(self.generated_opportunities) >= max_opportunities:
                    logger.info(
                        f"Target reached: {len(self.generated_opportunities)} opportunities"
                    )
                    break

                logger.info(
                    f"Processing signal {signal_id}: {SIGNAL_TYPES.get(signal_id, 'Unknown')}"
                )

                try:
                    opportunities = self.signal_processor.process_signal(signal_id, 10)
                    self.generated_opportunities.extend(opportunities)
                    self.processing_stats["signals_processed"] += 1

                    logger.info(
                        f"Signal {signal_id} completed: {len(opportunities)} opportunities"
                    )

                    # Brief pause between signals
                    time.sleep(2)

                except Exception as e:
                    logger.error(f"Error processing signal {signal_id}: {e}")
                    self.processing_stats["errors"] += 1
                    continue

            self.processing_stats["end_time"] = datetime.now()
            self.processing_stats["total_opportunities"] = len(
                self.generated_opportunities
            )

            logger.info(
                f"Lead generation completed: {len(self.generated_opportunities)} opportunities"
            )
            return self.generated_opportunities

        except Exception as e:
            logger.error(f"Lead generation failed: {e}")
            raise HRTechLeadGenerationError(f"Lead generation failed: {e}")

    def filter_and_deduplicate(
        self, opportunities: List[Opportunity]
    ) -> List[Opportunity]:
        """Filter and deduplicate opportunities"""
        if not opportunities:
            return []

        # Remove duplicates based on company and person
        seen = set()
        filtered = []

        for opp in opportunities:
            key = (opp.company.lower(), opp.person.lower())
            if key not in seen:
                seen.add(key)
                filtered.append(opp)

        # Sort by relevance score
        filtered.sort(key=lambda x: x.relevance_score, reverse=True)

        logger.info(
            f"Filtered {len(opportunities)} opportunities to {len(filtered)} unique opportunities"
        )
        return filtered

    def get_processing_stats(self) -> Dict[str, Any]:
        """Get processing statistics"""
        stats = self.processing_stats.copy()

        if stats["start_time"] and stats["end_time"]:
            duration = (stats["end_time"] - stats["start_time"]).total_seconds()
            stats["duration_seconds"] = duration
            stats["duration_minutes"] = duration / 60

        return stats

    def get_opportunities_by_signal(self) -> Dict[int, List[Opportunity]]:
        """Group opportunities by signal type"""
        by_signal = {}

        for opp in self.generated_opportunities:
            signal_type = opp.signal_type
            if signal_type not in by_signal:
                by_signal[signal_type] = []
            by_signal[signal_type].append(opp)

        return by_signal

    def get_quality_metrics(self) -> Dict[str, Any]:
        """Get quality metrics for generated opportunities"""
        if not self.generated_opportunities:
            return {
                "total_opportunities": 0,
                "average_relevance_score": 0,
                "high_quality_count": 0,
                "email_found_count": 0,
                "recent_opportunities": 0,
            }

        total = len(self.generated_opportunities)
        relevance_scores = [opp.relevance_score for opp in self.generated_opportunities]
        avg_relevance = sum(relevance_scores) / len(relevance_scores)

        high_quality = sum(1 for score in relevance_scores if score >= 0.8)
        email_found = sum(
            1
            for opp in self.generated_opportunities
            if opp.email != "Manual validation needed"
        )

        # Count recent opportunities (last 30 days)
        recent_count = 0
        thirty_days_ago = datetime.now().timestamp() - (30 * 24 * 60 * 60)
        for opp in self.generated_opportunities:
            try:
                opp_date = datetime.strptime(opp.date, "%Y-%m-%d").timestamp()
                if opp_date >= thirty_days_ago:
                    recent_count += 1
            except Exception:
                continue

        return {
            "total_opportunities": total,
            "average_relevance_score": round(avg_relevance, 3),
            "high_quality_count": high_quality,
            "email_found_count": email_found,
            "recent_opportunities": recent_count,
            "quality_percentage": round((high_quality / total) * 100, 1)
            if total > 0
            else 0,
        }
