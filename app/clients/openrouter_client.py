"""
OpenRouter client implementation for ToS Monitor.

This module provides the OpenRouter client for generating document comparison summaries
using multiple AI models through OpenRouter's unified API.
"""

import os
import logging
from typing import Optional, Dict, Any
import aiohttp
import json

from .base import BaseAIClient


logger = logging.getLogger(__name__)


class OpenRouterClient(BaseAIClient):
    """
    OpenRouter client for generating document comparison summaries.
    Supports multiple models through OpenRouter's unified API.
    """

    def __init__(self, api_key: str = None, model: str = "anthropic/claude-3.5-sonnet"):
        """
        Initialize OpenRouter client.

        Args:
            api_key: OpenRouter API key (if None, uses OPENROUTER_API_KEY env var)
            model: Model to use for comparisons (e.g., "anthropic/claude-3.5-sonnet", "openai/gpt-4")
        """
        api_key = api_key or os.getenv("OPENROUTER_API_KEY")
        model = model or os.getenv("OPENROUTER_MODEL", "anthropic/claude-3.5-sonnet")

        super().__init__(api_key, model, "openrouter")

        self.base_url = "https://openrouter.ai/api/v1"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

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

            # Prepare the request payload
            payload = {
                "model": self.model,
                "messages": [
                    {
                        "role": "system",
                        "content": "You are an expert legal analyst who specializes in comparing terms of service and legal documents. Your task is to identify and explain meaningful changes between document versions."
                    },
                    {
                        "role": "user",
                        "content": formatted_prompt
                    }
                ],
                "max_tokens": self.max_tokens,
                "temperature": self.temperature,
                "stream": False
            }

            # Make API call
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.base_url}/chat/completions",
                    headers=self.headers,
                    json=payload
                ) as response:
                    if response.status != 200:
                        logger.error(f"OpenRouter API error: {response.status} - {await response.text()}")
                        return None

                    data = await response.json()

                    if "choices" in data and data["choices"] and "message" in data["choices"][0]:
                        content = data["choices"][0]["message"]["content"]
                        logger.info(f"Successfully generated comparison for {document_name}")

                        # Log usage if available
                        if "usage" in data:
                            logger.debug(f"Token usage: {data['usage']}")

                        return content
                    else:
                        logger.error(f"No content returned from OpenRouter for {document_name}")
                        return None

        except Exception as e:
            logger.error(f"Failed to generate comparison for {document_name}: {str(e)}")
            return None

    async def test_connection(self) -> bool:
        """
        Test the connection to the OpenRouter service.

        Returns:
            bool: True if connection successful, False otherwise
        """
        try:
            payload = {
                "model": self.model,
                "messages": [
                    {
                        "role": "user",
                        "content": "Respond with 'OK' if you receive this message."
                    }
                ],
                "max_tokens": 10,
                "temperature": 0
            }

            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.base_url}/chat/completions",
                    headers=self.headers,
                    json=payload
                ) as response:
                    if response.status != 200:
                        logger.error(f"OpenRouter connection test failed: {response.status}")
                        return False

                    data = await response.json()

                    if "choices" in data and data["choices"] and "message" in data["choices"][0]:
                        content = data["choices"][0]["message"]["content"]
                        if "ok" in content.lower():
                            logger.info("OpenRouter connection test successful")
                            return True
                        else:
                            logger.error("OpenRouter connection test failed: unexpected response")
                            return False
                    else:
                        logger.error("OpenRouter connection test failed: no response content")
                        return False

        except Exception as e:
            logger.error(f"OpenRouter connection test failed: {str(e)}")
            return False