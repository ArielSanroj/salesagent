#!/usr/bin/env python3
"""
Custom Exceptions for HR Tech Lead Generation System
Defines specific exception types for better error handling
"""


class HRTechLeadGenerationError(Exception):
    """Base exception for HR Tech Lead Generation System"""
    pass


class CredentialsError(HRTechLeadGenerationError):
    """Raised when credentials are missing or invalid"""
    pass


class LLMServiceError(HRTechLeadGenerationError):
    """Raised when LLM service fails"""
    pass


class APIServiceError(HRTechLeadGenerationError):
    """Raised when external API service fails"""
    pass


class ScrapingError(HRTechLeadGenerationError):
    """Raised when web scraping fails"""
    pass


class EmailServiceError(HRTechLeadGenerationError):
    """Raised when email service fails"""
    pass


class ValidationError(HRTechLeadGenerationError):
    """Raised when data validation fails"""
    pass


class ConfigurationError(HRTechLeadGenerationError):
    """Raised when configuration is invalid"""
    pass


class RateLimitError(APIServiceError):
    """Raised when API rate limit is exceeded"""
    pass


class AuthenticationError(APIServiceError):
    """Raised when API authentication fails"""
    pass


class NetworkError(APIServiceError):
    """Raised when network connection fails"""
    pass
