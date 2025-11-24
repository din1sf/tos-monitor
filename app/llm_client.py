"""
LLM client integration for ToS Monitor.
Handles LLM operations for generating document comparison summaries.
"""

import os
import logging
from typing import Optional, Dict, Any
from openai import AsyncOpenAI


logger = logging.getLogger(__name__)


class LLMClient:
    """
    LLM client for generating document comparison summaries.
    Currently supports OpenAI GPT models.
    """

    def __init__(self, api_key: str = None, model: str = "gpt-4-turbo-preview"):
        """
        Initialize LLM client.

        Args:
            api_key: OpenAI API key (if None, uses OPENAI_API_KEY env var)
            model: Model to use for comparisons
        """
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OpenAI API key is required")

        self.model = model or os.getenv("LLM_MODEL", "gpt-4-turbo-preview")
        self.client = AsyncOpenAI(api_key=self.api_key)
        self.max_tokens = 4000
        self.temperature = 0.1  # Low temperature for consistent, focused output

        logger.info(f"Initialized LLM client with model: {self.model}")

    async def compare_documents(
        self,
        previous_content: str,
        current_content: str,
        document_name: str,
        prompt_template: str,
        metadata: Dict[str, Any] = None
    ) -> Optional[str]:
        """
        Generate a comparison summary between two document versions.

        Args:
            previous_content: Previous version of the document
            current_content: Current version of the document
            document_name: Name of the document being compared
            prompt_template: Prompt template for the comparison
            metadata: Additional metadata about the documents

        Returns:
            Optional[str]: Generated comparison summary or None if failed
        """
        try:
            # Prepare the prompt
            formatted_prompt = self._format_prompt(
                prompt_template,
                previous_content,
                current_content,
                document_name,
                metadata
            )

            # Make API call
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert legal analyst who specializes in comparing terms of service and legal documents. Your task is to identify and explain meaningful changes between document versions."
                    },
                    {
                        "role": "user",
                        "content": formatted_prompt
                    }
                ],
                max_tokens=self.max_tokens,
                temperature=self.temperature,
                stream=False
            )

            if response.choices and response.choices[0].message:
                content = response.choices[0].message.content
                logger.info(f"Successfully generated comparison for {document_name}")
                logger.debug(f"Token usage: {response.usage}")
                return content
            else:
                logger.error(f"No content returned from LLM for {document_name}")
                return None

        except Exception as e:
            logger.error(f"Failed to generate comparison for {document_name}: {str(e)}")
            return None

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

    async def test_connection(self) -> bool:
        """
        Test the connection to the LLM service.

        Returns:
            bool: True if connection successful, False otherwise
        """
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "user",
                        "content": "Respond with 'OK' if you receive this message."
                    }
                ],
                max_tokens=10,
                temperature=0
            )

            if response.choices and "ok" in response.choices[0].message.content.lower():
                logger.info("LLM connection test successful")
                return True
            else:
                logger.error("LLM connection test failed: unexpected response")
                return False

        except Exception as e:
            logger.error(f"LLM connection test failed: {str(e)}")
            return False

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
            "provider": "openai"
        }


def get_llm_client() -> LLMClient:
    """
    Get a configured LLM client instance.

    Returns:
        LLMClient: Configured LLM client
    """
    api_key = os.getenv("OPENAI_API_KEY")
    model = os.getenv("LLM_MODEL", "gpt-4-turbo-preview")

    if not api_key:
        raise ValueError("OPENAI_API_KEY environment variable is required")

    return LLMClient(api_key=api_key, model=model)