#!/usr/bin/env python3
"""
Performance Optimizer for HR Tech Lead Generation System
Coordinates async operations and uses LLM for optimization
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from async_scraper import AsyncScrapingService
from cache_manager import CacheManager

logger = logging.getLogger(__name__)


class PerformanceOptimizer:
    """Coordinates async operations and LLM-based optimization"""

    def __init__(self, llm_service=None):
        self.cache_manager = CacheManager()
        self.scraping_service = AsyncScrapingService(self.cache_manager)
        self.llm_service = llm_service
        self.optimization_history_file = Path("optimization_history.json")
        self.optimization_history = self._load_optimization_history()

    def _load_optimization_history(self) -> Dict[str, Any]:
        """Load optimization history from file"""
        if self.optimization_history_file.exists():
            try:
                with open(self.optimization_history_file, "r") as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"Error loading optimization history: {e}")
        return {
            "query_performance": {},
            "signal_optimizations": {},
            "successful_patterns": [],
            "last_optimization": None,
        }

    def _save_optimization_history(self) -> None:
        """Save optimization history to file"""
        try:
            with open(self.optimization_history_file, "w") as f:
                json.dump(self.optimization_history, f, indent=2)
        except Exception as e:
            logger.warning(f"Error saving optimization history: {e}")

    def optimize_llm_calls(self, queries: List[str], signal_id: int = None) -> List[str]:
        """Optimize queries using LLM based on historical performance"""
        if not self.llm_service:
            return self._simple_optimization(queries)

        return self._llm_optimization(queries, signal_id)

    def _simple_optimization(self, queries: List[str]) -> List[str]:
        """Simple query optimization without LLM"""
        optimized = []
        for query in queries:
            keywords = query.lower().split()
            if len(keywords) > 3:
                optimized.append(" ".join(keywords[:3]))
            else:
                optimized.append(query)
        return optimized

    def _llm_optimization(self, queries: List[str], signal_id: int) -> List[str]:
        """Optimize queries using LLM"""
        optimized = []

        for query in queries:
            query_key = f"{signal_id}_{query}" if signal_id else query
            perf = self.optimization_history.get("query_performance", {}).get(query_key, {})

            if perf and perf.get("success_rate", 0) < 0.3:
                improved = self._ask_llm_for_query(query, signal_id, perf)
                if improved:
                    optimized.append(improved)
                    continue

            optimized.append(query)

        return optimized

    def _ask_llm_for_query(self, query: str, signal_id: int, perf: Dict) -> Optional[str]:
        """Ask LLM to improve a query"""
        prompt = f"""Optimize this search query for HR tech lead generation.

Original query: "{query}"
Signal type: {signal_id if signal_id else 'General'}
Success rate: {perf.get('success_rate', 0):.1%}
Average relevance: {perf.get('avg_relevance', 0):.2f}

Return ONLY the optimized query, nothing else."""

        try:
            response = self.llm_service.invoke_sync(prompt, "query_optimization")
            if response and response != "Service temporarily unavailable":
                optimized = response.strip().strip('"').strip("'")
                if len(optimized) > 10:
                    logger.info(f"LLM optimized: '{query}' -> '{optimized}'")
                    return optimized
        except Exception as e:
            logger.warning(f"Error optimizing query with LLM: {e}")

        return None

    def get_optimized_queries_for_signal(
        self, signal_id: int, base_queries: List[str]
    ) -> List[str]:
        """Get optimized queries for a signal based on history"""
        if not self.llm_service:
            return base_queries

        signal_key = str(signal_id)
        optimizations = self.optimization_history.get("signal_optimizations", {})
        signal_opts = optimizations.get(signal_key, [])

        if signal_opts:
            latest = signal_opts[-1].get("analysis", {})
            suggestions = latest.get("query_suggestions", [])

            if suggestions and isinstance(suggestions, list):
                logger.info(f"Using LLM-optimized queries for signal {signal_id}")
                return suggestions[:len(base_queries)]

        return self.optimize_llm_calls(base_queries, signal_id)

    def analyze_and_optimize_from_results(
        self,
        opportunities: List[Any],
        queries_used: List[str],
        signal_id: int
    ) -> Dict[str, Any]:
        """Analyze results using LLM and generate optimization recommendations"""
        if not self.llm_service or not opportunities:
            return {"optimized": False, "reason": "No LLM or no opportunities"}

        metrics = self._calculate_metrics(opportunities)
        analysis = self._get_llm_analysis(opportunities, queries_used, signal_id, metrics)

        if analysis:
            self._update_history(queries_used, signal_id, metrics, analysis)
            return {"optimized": True, "analysis": analysis, "metrics": metrics}

        return {"optimized": False, "reason": "LLM analysis failed"}

    def _calculate_metrics(self, opportunities: List[Any]) -> Dict[str, Any]:
        """Calculate performance metrics"""
        total = len(opportunities)
        high_quality = sum(1 for o in opportunities if o.relevance_score >= 0.8)
        avg_rel = sum(o.relevance_score for o in opportunities) / total if total else 0
        emails = sum(1 for o in opportunities if o.email != "Manual validation needed")

        return {
            "total_opportunities": total,
            "high_quality": high_quality,
            "avg_relevance": avg_rel,
            "emails_found": emails,
        }

    def _get_llm_analysis(
        self, opportunities, queries, signal_id, metrics
    ) -> Optional[Dict]:
        """Get LLM analysis of results"""
        patterns = [
            {
                "company": o.company,
                "title": o.title[:100],
                "relevance": o.relevance_score,
            }
            for o in opportunities[:5]
            if o.relevance_score >= 0.7
        ]

        prompt = f"""Analyze HR tech lead generation results.

Signal Type: {signal_id}
Queries: {', '.join(queries)}

Results:
- Total: {metrics['total_opportunities']}
- High quality: {metrics['high_quality']}
- Avg relevance: {metrics['avg_relevance']:.2f}
- Emails found: {metrics['emails_found']}

Top patterns: {json.dumps(patterns, indent=2)}

Provide JSON with: "what_worked", "what_didnt_work", "query_suggestions", "recommendations"."""

        try:
            response = self.llm_service.invoke_sync(prompt, "performance_analysis")
            if response and response != "Service temporarily unavailable":
                try:
                    return json.loads(response)
                except:
                    return {"raw_analysis": response}
        except Exception as e:
            logger.warning(f"Error in LLM analysis: {e}")

        return None

    def _update_history(
        self, queries, signal_id, metrics, analysis
    ) -> None:
        """Update optimization history"""
        for query in queries:
            query_key = f"{signal_id}_{query}"
            if query_key not in self.optimization_history["query_performance"]:
                self.optimization_history["query_performance"][query_key] = {
                    "total_runs": 0,
                    "total_opportunities": 0,
                    "high_quality_count": 0,
                    "avg_relevance": 0.0,
                }

            perf = self.optimization_history["query_performance"][query_key]
            perf["total_runs"] += 1
            perf["total_opportunities"] += metrics["total_opportunities"]
            perf["high_quality_count"] += metrics["high_quality"]
            n = perf["total_runs"]
            perf["avg_relevance"] = (perf["avg_relevance"] * (n - 1) + metrics["avg_relevance"]) / n
            perf["success_rate"] = perf["high_quality_count"] / max(perf["total_opportunities"], 1)

        signal_key = str(signal_id)
        if signal_key not in self.optimization_history["signal_optimizations"]:
            self.optimization_history["signal_optimizations"][signal_key] = []

        self.optimization_history["signal_optimizations"][signal_key].append({
            "timestamp": datetime.now().isoformat(),
            "analysis": analysis,
            "metrics": metrics,
        })
        self.optimization_history["signal_optimizations"][signal_key] = \
            self.optimization_history["signal_optimizations"][signal_key][-10:]

        self.optimization_history["last_optimization"] = datetime.now().isoformat()
        self._save_optimization_history()

        logger.info(f"LLM analysis completed for signal {signal_id}")

    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get performance metrics"""
        return self.cache_manager.get_cache_stats()

    def batch_process_opportunities(
        self, opportunities: List[Any], batch_size: int = 10
    ) -> List[List[Any]]:
        """Process opportunities in batches"""
        return [
            opportunities[i:i + batch_size]
            for i in range(0, len(opportunities), batch_size)
        ]
