"""
Base classes and protocols for AI clients.

This module defines the common interface and base functionality
that all AI client implementations must follow.
"""

import logging
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, Protocol


logger = logging.getLogger(__name__)


class AIClient(Protocol):
    """
    Protocol definition for AI clients.
    All AI client implementations must follow this interface.
    """

    async def compare_documents(
        self,
        previous_content: str,
        current_content: str,
        document_name: str,
        prompt_template: str,
        metadata: Dict[str, Any] = None
    ) -> Optional[str]:
        """Generate a comparison summary between two document versions."""
        ...

    async def test_connection(self) -> bool:
        """Test the connection to the AI service."""
        ...

    async def get_model_info(self) -> Dict[str, Any]:
        """Get information about the current model."""
        ...


class BaseAIClient(ABC):
    """
    Abstract base class for AI clients.
    Provides common functionality and enforces the interface.
    """

    def __init__(self, api_key: str, model: str, provider: str):
        """
        Initialize base AI client.

        Args:
            api_key: API key for the service
            model: Model to use
            provider: Provider name
        """
        self.api_key = api_key
        self.model = model
        self.provider = provider
        self.max_tokens = 4000
        self.temperature = 0.1

        if not self.api_key:
            raise ValueError(f"{provider} API key is required")

        logger.info(f"Initialized {provider} client with model: {model}")

    @abstractmethod
    async def compare_documents(
        self,
        previous_content: str,
        current_content: str,
        document_name: str,
        prompt_template: str,
        metadata: Dict[str, Any] = None
    ) -> Optional[str]:
        """Generate a comparison summary between two document versions."""
        pass

    @abstractmethod
    async def test_connection(self) -> bool:
        """Test the connection to the AI service."""
        pass

    async def get_model_info(self) -> Dict[str, Any]:
        """
        Get information about the current model.

        Returns:
            Dict[str, Any]: Model information
        """
        return {
            "model": self.model,
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
            "provider": self.provider
        }

    def _format_prompt(
        self,
        template: str,
        previous_content: str,
        current_content: str,
        document_name: str,
        metadata: Dict[str, Any] = None
    ) -> str:
        """
        Format the prompt template with document content and metadata.

        Args:
            template: Prompt template
            previous_content: Previous document version
            current_content: Current document version
            document_name: Document name
            metadata: Additional metadata

        Returns:
            str: Formatted prompt
        """
        # Truncate content if too long
        max_content_length = 15000  # Leave room for prompt and response

        if len(previous_content) > max_content_length:
            previous_content = previous_content[:max_content_length] + "...[truncated]"

        if len(current_content) > max_content_length:
            current_content = current_content[:max_content_length] + "...[truncated]"

        # Format metadata
        metadata_str = ""
        if metadata:
            metadata_items = []
            for key, value in metadata.items():
                if key not in ["content_hash", "raw_content"]:  # Skip large/internal fields
                    metadata_items.append(f"{key}: {value}")
            metadata_str = "\n".join(metadata_items)

        # Replace placeholders in template
        formatted_prompt = template.format(
            document_name=document_name,
            previous_content=previous_content,
            current_content=current_content,
            metadata=metadata_str
        )

        return formatted_prompt