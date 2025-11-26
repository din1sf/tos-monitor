"""
LLM client integration for ToS Monitor.
Handles LLM operations for generating document comparison summaries.
Supports multiple AI providers through a flexible interface.

This module provides factory functions and backward compatibility
for the AI client system.
"""

import os
import logging
from typing import Union

from .clients import AIClient, OpenAIClient, OpenRouterClient


logger = logging.getLogger(__name__)


# Legacy alias for backward compatibility
LLMClient = OpenAIClient


def get_llm_client(provider: str = None) -> AIClient:
    """
    Get a configured AI client instance.

    Args:
        provider: AI provider to use ("openai", "openrouter").
                 If None, uses AI_PROVIDER env var (default: "openai")

    Returns:
        AIClient: Configured AI client instance
    """
    if provider is None:
        provider = os.getenv("AI_PROVIDER", "openai")

    if provider.lower() == "openai":
        api_key = os.getenv("OPENAI_API_KEY")
        model = os.getenv("LLM_MODEL", "gpt-4-turbo-preview")

        if not api_key:
            raise ValueError("OPENAI_API_KEY environment variable is required")

        return OpenAIClient(api_key=api_key, model=model)

    elif provider.lower() == "openrouter":
        api_key = os.getenv("OPENROUTER_API_KEY")
        model = os.getenv("OPENROUTER_MODEL", "anthropic/claude-3.5-sonnet")

        if not api_key:
            raise ValueError("OPENROUTER_API_KEY environment variable is required")

        return OpenRouterClient(api_key=api_key, model=model)

    else:
        raise ValueError(f"Unsupported provider: {provider}. Supported providers: openai, openrouter")


def get_openai_client() -> OpenAIClient:
    """
    Get a configured OpenAI client instance.

    Returns:
        OpenAIClient: Configured OpenAI client
    """
    return get_llm_client("openai")


def get_openrouter_client() -> OpenRouterClient:
    """
    Get a configured OpenRouter client instance.

    Returns:
        OpenRouterClient: Configured OpenRouter client
    """
    return get_llm_client("openrouter")


def create_client(
    provider: str,
    api_key: str = None,
    model: str = None
) -> Union[OpenAIClient, OpenRouterClient]:
    """
    Create a specific AI client with custom parameters.

    Args:
        provider: Provider name ("openai", "openrouter")
        api_key: API key (if None, uses environment variable)
        model: Model name (if None, uses default for provider)

    Returns:
        Union[OpenAIClient, OpenRouterClient]: Configured client instance
    """
    if provider.lower() == "openai":
        return OpenAIClient(api_key=api_key, model=model)
    elif provider.lower() == "openrouter":
        return OpenRouterClient(api_key=api_key, model=model)
    else:
        raise ValueError(f"Unsupported provider: {provider}")


# Export commonly used classes and functions
__all__ = [
    "AIClient",
    "OpenAIClient",
    "OpenRouterClient",
    "LLMClient",
    "get_llm_client",
    "get_openai_client",
    "get_openrouter_client",
    "create_client"
]