#!/usr/bin/env python3
"""
Checkpoint Manager for Lead Generation
Handles saving and loading progress checkpoints
"""

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


class CheckpointManager:
    """Manages checkpoints for lead generation progress"""

    def __init__(self, checkpoint_dir: str = "checkpoints"):
        self.checkpoint_dir = Path(checkpoint_dir)
        self.checkpoint_dir.mkdir(exist_ok=True)

    def save_checkpoint(
        self,
        opportunities: List[Any],
        stats: Dict[str, Any],
        filename: str = None
    ) -> str:
        """Save current progress to checkpoint file"""
        if filename is None:
            timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
            filename = f"checkpoint_opportunities_{timestamp}.json"

        checkpoint_path = self.checkpoint_dir / filename

        try:
            data = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "opportunities": [self._to_dict(opp) for opp in opportunities],
                "stats": stats.copy() if stats else {},
            }

            checkpoint_path.write_text(json.dumps(data, indent=2, default=str))
            logger.info(f"Checkpoint saved: {len(opportunities)} opportunities -> {checkpoint_path}")
            return str(checkpoint_path)

        except Exception as e:
            logger.error(f"Error saving checkpoint: {e}")
            return ""

    def load_checkpoint(self, checkpoint_path: str) -> List[Dict]:
        """Load opportunities from checkpoint file"""
        try:
            path = Path(checkpoint_path)
            if not path.exists():
                logger.warning(f"Checkpoint file not found: {checkpoint_path}")
                return []

            data = json.loads(path.read_text())
            opportunities = data.get("opportunities", [])

            logger.info(f"Loaded {len(opportunities)} opportunities from checkpoint")
            return opportunities

        except Exception as e:
            logger.error(f"Error loading checkpoint: {e}")
            return []

    def _to_dict(self, opp) -> Dict[str, Any]:
        """Convert opportunity to dictionary"""
        if hasattr(opp, 'to_dict'):
            return opp.to_dict()

        return {
            "title": getattr(opp, 'title', ''),
            "company": getattr(opp, 'company', ''),
            "person": getattr(opp, 'person', ''),
            "email": getattr(opp, 'email', ''),
            "url": getattr(opp, 'url', ''),
            "date": getattr(opp, 'date', ''),
            "content": getattr(opp, 'content', ''),
            "relevance_score": getattr(opp, 'relevance_score', 0.0),
            "signal_type": getattr(opp, 'signal_type', 1),
            "source": getattr(opp, 'source', ''),
        }
