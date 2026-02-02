#!/usr/bin/env python3
"""
Quality Analyzer for Lead Generation
Handles metrics calculation and quality analysis
"""

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List

try:
    from rapidfuzz import fuzz
except ImportError:
    fuzz = None

logger = logging.getLogger(__name__)


class QualityAnalyzer:
    """Analyzes quality metrics for generated opportunities"""

    def __init__(self, signal_types: Dict[int, str]):
        self.signal_types = signal_types

    def calculate_similarity(self, a: str, b: str) -> float:
        """Calculate similarity between two strings"""
        if not a or not b:
            return 0.0

        if fuzz:
            return fuzz.ratio(a.lower(), b.lower())
        else:
            return 100.0 if a.lower() == b.lower() else 0.0

    def filter_and_deduplicate(
        self,
        opportunities: List[Any],
        similarity_threshold: int = 90,
        use_email_as_key: bool = True,
    ) -> List[Any]:
        """Filter and deduplicate opportunities with fuzzy matching"""
        if not opportunities:
            return []

        seen = []
        filtered = []

        for opp in opportunities:
            duplicate = False

            # Check by email first
            if use_email_as_key and opp.email and opp.email != "Manual validation needed":
                for existing in seen:
                    if existing.email and existing.email != "Manual validation needed":
                        if opp.email.lower() == existing.email.lower():
                            duplicate = True
                            break

            # Check by company + person similarity
            if not duplicate:
                for existing in seen:
                    company_sim = self.calculate_similarity(opp.company, existing.company)
                    person_sim = self.calculate_similarity(opp.person, existing.person)

                    if company_sim >= similarity_threshold and person_sim >= similarity_threshold:
                        duplicate = True
                        break

            if not duplicate:
                seen.append(opp)
                filtered.append(opp)

        filtered.sort(key=lambda x: x.relevance_score, reverse=True)

        logger.info(
            f"Filtered {len(opportunities)} to {len(filtered)} unique "
            f"({len(opportunities) - len(filtered)} duplicates removed)"
        )
        return filtered

    def get_quality_metrics(self, opportunities: List[Any]) -> Dict[str, Any]:
        """Get comprehensive quality metrics"""
        if not opportunities:
            return self._empty_metrics()

        total = len(opportunities)
        relevance_scores = [opp.relevance_score for opp in opportunities]
        avg_relevance = sum(relevance_scores) / len(relevance_scores)

        high_quality = sum(1 for s in relevance_scores if s >= 0.8)
        email_found = sum(
            1 for opp in opportunities
            if opp.email and opp.email != "Manual validation needed"
        )

        recent_count = self._count_recent(opportunities)
        signals_distribution = self._get_signals_distribution(opportunities)
        quality_tiers = self._get_quality_tiers(relevance_scores)
        success_by_signal = self._get_success_by_signal(signals_distribution, total)

        return {
            "total_opportunities": total,
            "average_relevance_score": round(avg_relevance, 3),
            "high_quality_count": high_quality,
            "email_found_count": email_found,
            "recent_opportunities": recent_count,
            "quality_percentage": round((high_quality / total) * 100, 1),
            "email_found_percentage": round((email_found / total) * 100, 1),
            "recent_percentage": round((recent_count / total) * 100, 1),
            "signals_distribution": signals_distribution,
            "success_rate_by_signal": success_by_signal,
            "quality_tiers": quality_tiers,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    def _empty_metrics(self) -> Dict[str, Any]:
        """Return empty metrics"""
        return {
            "total_opportunities": 0,
            "average_relevance_score": 0,
            "high_quality_count": 0,
            "email_found_count": 0,
            "recent_opportunities": 0,
            "quality_percentage": 0,
            "signals_distribution": {},
            "success_rate_by_signal": {},
        }

    def _count_recent(self, opportunities: List[Any]) -> int:
        """Count opportunities from last 30 days"""
        count = 0
        thirty_days_ago = datetime.now(timezone.utc).timestamp() - (30 * 24 * 60 * 60)

        for opp in opportunities:
            try:
                opp_date = datetime.strptime(opp.date, "%Y-%m-%d")
                opp_date = opp_date.replace(tzinfo=timezone.utc).timestamp()
                if opp_date >= thirty_days_ago:
                    count += 1
            except Exception:
                continue

        return count

    def _get_signals_distribution(self, opportunities: List[Any]) -> Dict[int, int]:
        """Get distribution by signal type"""
        distribution = {}
        for opp in opportunities:
            signal = opp.signal_type
            distribution[signal] = distribution.get(signal, 0) + 1
        return distribution

    def _get_quality_tiers(self, scores: List[float]) -> Dict[str, int]:
        """Get quality tier counts"""
        return {
            "excellent": sum(1 for s in scores if s >= 0.9),
            "high": sum(1 for s in scores if 0.8 <= s < 0.9),
            "medium": sum(1 for s in scores if 0.7 <= s < 0.8),
            "low": sum(1 for s in scores if s < 0.7),
        }

    def _get_success_by_signal(
        self, distribution: Dict[int, int], total: int
    ) -> Dict[str, Dict]:
        """Get success rate by signal"""
        success_rate = {}
        for signal_id, count in distribution.items():
            name = self.signal_types.get(signal_id, f"Signal {signal_id}")
            success_rate[name] = {
                "count": count,
                "percentage": round((count / total) * 100, 1) if total else 0,
            }
        return success_rate
