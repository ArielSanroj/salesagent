#!/usr/bin/env python3
"""
Cache Manager for HR Tech Lead Generation System
Handles caching for scraped content and API responses
"""

import hashlib
import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class CacheManager:
    """Manages caching for scraped content and API responses"""

    def __init__(self, cache_dir: str = "cache", ttl_hours: int = 24):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
        self.ttl_hours = ttl_hours

    def _get_cache_key(self, url: str) -> str:
        """Generate cache key for URL"""
        return hashlib.md5(url.encode()).hexdigest()

    def _get_cache_path(self, cache_key: str) -> Path:
        """Get cache file path"""
        return self.cache_dir / f"{cache_key}.json"

    def get_cached_content(self, url: str) -> Optional[Dict[str, Any]]:
        """Get cached content for URL"""
        cache_key = self._get_cache_key(url)
        cache_path = self._get_cache_path(cache_key)

        if not cache_path.exists():
            return None

        try:
            with open(cache_path, "r") as f:
                data = json.load(f)

            # Check TTL
            cached_time = datetime.fromisoformat(data["timestamp"])
            if datetime.now() - cached_time > timedelta(hours=self.ttl_hours):
                cache_path.unlink()
                return None

            logger.info(f"Cache hit for {url}")
            return data["content"]

        except Exception as e:
            logger.warning(f"Error reading cache for {url}: {e}")
            return None

    def set_cached_content(self, url: str, content: Dict[str, Any]) -> None:
        """Cache content for URL"""
        cache_key = self._get_cache_key(url)
        cache_path = self._get_cache_path(cache_key)

        try:
            data = {"timestamp": datetime.now().isoformat(), "content": content}

            with open(cache_path, "w") as f:
                json.dump(data, f)

            logger.info(f"Cached content for {url}")

        except Exception as e:
            logger.warning(f"Error caching content for {url}: {e}")

    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        cache_files = list(self.cache_dir.glob("*.json"))
        return {
            "cache_size": len(cache_files),
            "cache_dir": str(self.cache_dir),
            "timestamp": datetime.now().isoformat(),
        }
