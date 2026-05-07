"""
Bosch LLM Farm client implementation for ToS Monitor.

This module provides the Bosch LLM Farm client for generating document comparison summaries
using Anthropic models (Claude) through Bosch's internal infrastructure with custom authentication.
Uses Anthropic's native API format via the rawPredict endpoint.
"""

import os
import logging
from typing import Optional, Dict, Any
import aiohttp
import json

from .base import BaseAIClient


logger = logging.getLogger(__name__)


class BoschLLMFarmClient(BaseAIClient):
    """
    Bosch LLM Farm client for generating document comparison summaries.
    Supports Anthropic Claude models through Bosch's internal endpoint with Bearer token authentication.
    Uses Anthropic's native API format (messages, system, max_tokens).
    """

    def __init__(self, auth_token: str = None, model: str = None):
        """
        Initialize Bosch LLM Farm client.

        Args:
            auth_token: Bosch Farm authentication token (if None, uses ANTHROPIC_AUTH_TOKEN env var)
            model: Model to use for comparisons (if None, uses BOSCH_LLM_MODEL env var - required)
        """
        auth_token = auth_token or os.getenv("ANTHROPIC_AUTH_TOKEN")
        model = model or os.getenv("BOSCH_LLM_MODEL")

        # Validate model is provided (no default)
        if not model:
            raise ValueError("BOSCH_LLM_MODEL environment variable is required")

        super().__init__(auth_token, model, "bosch-llm-farm")

        self.base_url = os.getenv(
            "BOSCH_LLM_BASE_URL",
            "https://aoai-farm.bosch-temp.com/api/google/v1"
        )
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        self.anthropic_version = "vertex-2023-10-16"

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
            # Prepare the prompt using inherited method
            formatted_prompt = self._format_prompt(
                prompt_template,
                previous_content,
                current_content,
                document_name,
                metadata
            )

            # Prepare the request payload in Anthropic native format
            payload = {
                "anthropic_version": self.anthropic_version,
                "system": "You are an expert legal analyst who specializes in comparing terms of service and legal documents. Your task is to identify and explain meaningful changes between document versions.",
                "messages": [
                    {
                        "role": "user",
                        "content": formatted_prompt
                    }
                ],
                "max_tokens": self.max_tokens,
                "temperature": self.temperature
            }

            # Construct endpoint URL with model
            endpoint = f"{self.base_url}/publishers/anthropic/models/{self.model}:rawPredict"

            # Make API call
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    endpoint,
                    headers=self.headers,
                    json=payload
                ) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        logger.error(f"Bosch LLM Farm API error: {response.status} - {error_text}")
                        return None

                    data = await response.json()

                    # Parse Anthropic response format
                    if "content" in data and data["content"]:
                        # Extract text from content array
                        content_parts = data["content"]
                        text_parts = [part["text"] for part in content_parts if part.get("type") == "text"]

                        if text_parts:
                            content = "\n".join(text_parts)
                            logger.info(f"Successfully generated comparison for {document_name}")

                            # Log usage if available
                            if "usage" in data:
                                usage = data["usage"]
                                logger.debug(
                                    f"Token usage: input={usage.get('input_tokens')}, "
                                    f"output={usage.get('output_tokens')}"
                                )

                            return content
                        else:
                            logger.error(f"No text content in response for {document_name}")
                            return None
                    else:
                        logger.error(f"No content returned from Bosch LLM Farm for {document_name}")
                        return None

        except Exception as e:
            logger.error(f"Failed to generate comparison for {document_name}: {str(e)}")
            return None

    async def test_connection(self) -> bool:
        """
        Test the connection to the Bosch LLM Farm service.

        Returns:
            bool: True if connection successful, False otherwise
        """
        try:
            payload = {
                "anthropic_version": self.anthropic_version,
                "messages": [
                    {
                        "role": "user",
                        "content": "Respond with 'OK' if you receive this message."
                    }
                ],
                "max_tokens": 10,
                "temperature": 0
            }

            # Construct endpoint URL with model
            endpoint = f"{self.base_url}/publishers/anthropic/models/{self.model}:rawPredict"

            async with aiohttp.ClientSession() as session:
                async with session.post(
                    endpoint,
                    headers=self.headers,
                    json=payload
                ) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        logger.error(f"Bosch LLM Farm connection test failed: {response.status} - {error_text}")
                        return False

                    data = await response.json()

                    if "content" in data and data["content"]:
                        # Extract text from content array
                        content_parts = data["content"]
                        text_parts = [part["text"] for part in content_parts if part.get("type") == "text"]

                        if text_parts:
                            content = " ".join(text_parts)
                            if "ok" in content.lower():
                                logger.info("Bosch LLM Farm connection test successful")
                                return True
                            else:
                                logger.warning(f"Bosch LLM Farm connection test: unexpected response '{content}'")
                                # Still consider it successful if we got a response
                                return True
                        else:
                            logger.error("Bosch LLM Farm connection test failed: no text content")
                            return False
                    else:
                        logger.error("Bosch LLM Farm connection test failed: no content in response")
                        return False

        except Exception as e:
            logger.error(f"Bosch LLM Farm connection test failed: {str(e)}")
            return False
