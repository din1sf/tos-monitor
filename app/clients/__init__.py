"""
AI Clients package for ToS Monitor.

This package contains various AI client implementations for different providers.
All clients follow the AIClient protocol defined in base.py.
"""

from .base import AIClient, BaseAIClient
from .openai_client import OpenAIClient
from .openrouter_client import OpenRouterClient

__all__ = [
    "AIClient",
    "BaseAIClient",
    "OpenAIClient",
    "OpenRouterClient"
]