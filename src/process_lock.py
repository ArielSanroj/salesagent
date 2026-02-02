#!/usr/bin/env python3
"""
Process Lock Management for HR Tech Lead Generation System
Prevents multiple instances from running simultaneously
"""

import fcntl
import logging
import os
from typing import Optional

logger = logging.getLogger(__name__)


class ProcessLock:
    """Manages process locking to prevent multiple instances"""

    def __init__(self, lock_file: str):
        self.lock_file = lock_file
        self._lock_fd: Optional[int] = None

    def acquire(self) -> bool:
        """Acquire a lock to prevent multiple instances from running"""
        try:
            self._lock_fd = os.open(self.lock_file, os.O_CREAT | os.O_WRONLY | os.O_TRUNC)
            fcntl.flock(self._lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            os.write(self._lock_fd, str(os.getpid()).encode())
            os.close(self._lock_fd)
            logger.info(f"Lock acquired successfully (PID: {os.getpid()})")
            return True
        except (OSError, IOError) as e:
            logger.error(f"Could not acquire lock: {e}")
            print("Another instance is already running!")
            print(f"If you're sure no other instance is running, delete: rm {self.lock_file}")
            return False

    def release(self) -> None:
        """Release the process lock"""
        try:
            if os.path.exists(self.lock_file):
                os.unlink(self.lock_file)
                logger.info("Lock released successfully")
        except OSError:
            pass

    def __enter__(self):
        """Context manager entry"""
        if not self.acquire():
            raise RuntimeError("Could not acquire process lock")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.release()
        return False


def acquire_lock(lock_file: str) -> bool:
    """Convenience function to acquire lock"""
    lock = ProcessLock(lock_file)
    return lock.acquire()


def release_lock(lock_file: str) -> None:
    """Convenience function to release lock"""
    try:
        if os.path.exists(lock_file):
            os.unlink(lock_file)
            logger.info("Lock released successfully")
    except OSError:
        pass
