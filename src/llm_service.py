#!/usr/bin/env python3
"""
Resilient LLM Service with Retry and Fallback Mechanisms
Handles LLM service failures gracefully without aborting the application
"""

import asyncio
import logging
import queue
import threading
import time
from concurrent.futures import ThreadPoolExecutor, TimeoutError
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional

from langchain_core.prompts import PromptTemplate
from langchain_ollama import ChatOllama

from credentials_manager import CredentialsManager


class LLMStatus(Enum):
    """LLM service status"""

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    FAILED = "failed"
    UNAVAILABLE = "unavailable"


@dataclass
class LLMResponse:
    """LLM response wrapper"""

    content: str
    success: bool
    error: Optional[str] = None
    retry_count: int = 0
    fallback_used: bool = False


class LLMService:
    """Resilient LLM service with retry, fallback, and queue mechanisms"""

    def __init__(self, credentials_manager: CredentialsManager):
        self.credentials_manager = credentials_manager
        self.logger = logging.getLogger(__name__)

        # Service state
        self.status = LLMStatus.UNAVAILABLE
        self.llm_client = None
        self.retry_count = 0
        self.max_retries = 3
        self.retry_delay = 2
        self.timeout = 30

        # Queue for managing requests
        self.request_queue = queue.Queue(maxsize=100)
        self.response_queue = queue.Queue(maxsize=100)
        self.worker_thread = None
        self.shutdown_event = threading.Event()

        # Fallback responses
        self.fallback_responses = {
            "email_finder": "Manual validation needed",
            "content_parser": "Content parsing failed - manual review required",
            "relevance_scorer": "Unable to score relevance - manual review required",
        }

        # Initialize the service
        self._initialize_service()

    def _initialize_service(self):
        """Initialize the LLM service with retry logic"""
        try:
            # Try to initialize Ollama LLM service
            ollama_config = self.credentials_manager.get_ollama_config()
            self.max_retries = ollama_config.get("max_retries", 3)
            self.retry_delay = ollama_config.get("retry_delay", 2)
            self.timeout = ollama_config.get("timeout", 30)

            self.llm_client = ChatOllama(
                model=ollama_config["model"],
                base_url=ollama_config["base_url"],
            )

            # Test the connection
            self._test_connection()

        except Exception as e:
            self.logger.error(f"Failed to initialize LLM service: {e}")
            self.status = LLMStatus.FAILED
            # Don't raise - allow the service to run in degraded mode

    def _test_connection(self):
        """Test LLM connection with retry logic"""
        for attempt in range(self.max_retries):
            try:
                test_response = self.llm_client.invoke("Test: What is HR tech?")
                if test_response and hasattr(test_response, "content"):
                    self.logger.info(
                        f"LLM connection test successful: {test_response.content[:100]}..."
                    )
                    self.status = LLMStatus.HEALTHY
                    self.retry_count = 0
                    return
                else:
                    raise ValueError("Invalid response from LLM")

            except Exception as e:
                self.logger.warning(
                    f"LLM connection test attempt {attempt + 1}/{self.max_retries} failed: {e}"
                )
                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay * (2**attempt))
                else:
                    self.logger.error("LLM connection test failed after all retries")
                    self.status = LLMStatus.FAILED
                    raise

    def start_worker_thread(self):
        """Start the background worker thread for processing requests"""
        if self.worker_thread is None or not self.worker_thread.is_alive():
            self.worker_thread = threading.Thread(target=self._worker_loop, daemon=True)
            self.worker_thread.start()
            self.logger.info("LLM service worker thread started")

    def stop_worker_thread(self):
        """Stop the background worker thread"""
        self.shutdown_event.set()
        if self.worker_thread and self.worker_thread.is_alive():
            self.worker_thread.join(timeout=5)
        self.logger.info("LLM service worker thread stopped")

    def _worker_loop(self):
        """Background worker loop for processing LLM requests"""
        while not self.shutdown_event.is_set():
            try:
                # Get request from queue with timeout
                request = self.request_queue.get(timeout=1)
                if request is None:  # Shutdown signal
                    break

                # Process the request
                response = self._process_request(request)

                # Put response in response queue
                self.response_queue.put(response)

            except queue.Empty:
                continue
            except Exception as e:
                self.logger.error(f"Error in worker loop: {e}")

    def _process_request(self, request: Dict[str, Any]) -> LLMResponse:
        """Process a single LLM request"""
        try:
            if self.status == LLMStatus.FAILED:
                return self._get_fallback_response(request)

            # Try to process with LLM
            response = self._call_llm_with_retry(request)
            return response

        except Exception as e:
            self.logger.error(f"Error processing request: {e}")
            return self._get_fallback_response(request)

    def _call_llm_with_retry(self, request: Dict[str, Any]) -> LLMResponse:
        """Call LLM with retry logic"""
        for attempt in range(self.max_retries):
            try:
                if self.status == LLMStatus.FAILED:
                    # Try to recover
                    self._attempt_recovery()

                if self.status == LLMStatus.FAILED:
                    return self._get_fallback_response(request)

                # Make the actual LLM call
                response = self.llm_client.invoke(request["prompt"])

                if response and hasattr(response, "content"):
                    content = response.content.strip()
                    self.logger.info(f"LLM request successful (attempt {attempt + 1})")
                    return LLMResponse(
                        content=content, success=True, retry_count=attempt
                    )
                else:
                    raise ValueError("Invalid response from LLM")

            except Exception as e:
                self.logger.warning(
                    f"LLM call attempt {attempt + 1}/{self.max_retries} failed: {e}"
                )

                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay * (2**attempt))
                else:
                    self.logger.error("LLM call failed after all retries")
                    self.status = LLMStatus.FAILED
                    return self._get_fallback_response(request)

    def _attempt_recovery(self):
        """Attempt to recover the LLM service"""
        try:
            self.logger.info("Attempting to recover LLM service...")
            self._test_connection()
            self.logger.info("LLM service recovered successfully")
        except Exception as e:
            self.logger.error(f"LLM service recovery failed: {e}")

    def _get_fallback_response(self, request: Dict[str, Any]) -> LLMResponse:
        """Get fallback response when LLM is unavailable"""
        request_type = request.get("type", "unknown")
        fallback_content = self.fallback_responses.get(
            request_type, "Service temporarily unavailable"
        )

        self.logger.warning(f"Using fallback response for {request_type}")

        return LLMResponse(
            content=fallback_content,
            success=False,
            error="LLM service unavailable",
            fallback_used=True,
        )

    def invoke_async(self, prompt: str, request_type: str = "general") -> str:
        """Invoke LLM asynchronously (non-blocking)"""
        if self.status == LLMStatus.FAILED:
            return self.fallback_responses.get(
                request_type, "Service temporarily unavailable"
            )

        # Start worker thread if not running
        self.start_worker_thread()

        # Add request to queue
        request = {"prompt": prompt, "type": request_type, "timestamp": time.time()}

        try:
            self.request_queue.put(request, timeout=1)

            # Try to get response with timeout
            response = self.response_queue.get(timeout=self.timeout)
            return response.content

        except queue.Full:
            self.logger.warning("Request queue full, using fallback")
            return self.fallback_responses.get(
                request_type, "Service temporarily unavailable"
            )
        except queue.Empty:
            self.logger.warning("Response timeout, using fallback")
            return self.fallback_responses.get(
                request_type, "Service temporarily unavailable"
            )

    def invoke_sync(self, prompt: str, request_type: str = "general") -> str:
        """Invoke LLM synchronously (blocking)"""
        if self.status == LLMStatus.FAILED:
            return self.fallback_responses.get(
                request_type, "Service temporarily unavailable"
            )

        try:
            response = self.llm_client.invoke(prompt)
            if response and hasattr(response, "content"):
                return response.content.strip()
            else:
                raise ValueError("Invalid response from LLM")

        except Exception as e:
            self.logger.error(f"LLM sync call failed: {e}")
            self.status = LLMStatus.DEGRADED
            return self.fallback_responses.get(
                request_type, "Service temporarily unavailable"
            )

    def get_status(self) -> Dict[str, Any]:
        """Get current service status"""
        return {
            "status": self.status.value,
            "retry_count": self.retry_count,
            "queue_size": self.request_queue.qsize(),
            "worker_alive": self.worker_thread.is_alive()
            if self.worker_thread
            else False,
        }

    def health_check(self) -> bool:
        """Perform health check on the service"""
        try:
            if self.status == LLMStatus.FAILED:
                self._attempt_recovery()

            return self.status in [LLMStatus.HEALTHY, LLMStatus.DEGRADED]

        except Exception as e:
            self.logger.error(f"Health check failed: {e}")
            return False

    def __del__(self):
        """Cleanup when service is destroyed"""
        self.stop_worker_thread()
