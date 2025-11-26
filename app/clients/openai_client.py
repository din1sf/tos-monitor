"""
OpenAI client implementation for ToS Monitor.

This module provides the OpenAI client for generating document comparison summaries
using OpenAI's GPT models.
"""

import os
import logging
from typing import Optional, Dict, Any
from openai import AsyncOpenAI

from .base import BaseAIClient


logger = logging.getLogger(__name__)


class OpenAIClient(BaseAIClient):
    """
    OpenAI client for generating document comparison summaries.
    Supports OpenAI GPT models.
    """

    def __init__(self, api_key: str = None, model: str = "gpt-4-turbo-preview"):
        """
        Initialize OpenAI client.

        Args:
            api_key: OpenAI API key (if None, uses OPENAI_API_KEY env var)
            model: Model to use for comparisons
        """
        api_key = api_key or os.getenv("OPENAI_API_KEY")
        model = model or os.getenv("LLM_MODEL", "gpt-4-turbo-preview")

        super().__init__(api_key, model, "openai")

        self.client = AsyncOpenAI(api_key=self.api_key)

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

    async def test_connection(self) -> bool:
        """
        Test the connection to the OpenAI service.

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
                logger.info("OpenAI connection test successful")
                return True
            else:
                logger.error("OpenAI connection test failed: unexpected response")
                return False

        except Exception as e:
            logger.error(f"OpenAI connection test failed: {str(e)}")
            return False