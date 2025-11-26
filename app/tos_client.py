"""
ToS Client - High-level orchestrator for Terms of Service document analysis.

This module provides a unified interface for analyzing ToS document changes
using AI providers. It handles template loading, AI client creation,
and the complete analysis workflow.
"""

import os
import logging
from typing import Optional, Dict, Any, Union
from pathlib import Path

from .llm_client import get_llm_client, AIClient
from .storage import get_storage_client


logger = logging.getLogger(__name__)


class ToSClient:
    """
    High-level client for ToS document analysis.

    This class orchestrates the complete workflow:
    1. Load prompt templates
    2. Create appropriate AI client
    3. Format prompts with document content
    4. Send analysis requests
    5. Handle responses and approval workflow
    """

    def __init__(
        self,
        ai_provider: str = None,
        prompt_template_path: str = None,
        storage_client = None
    ):
        """
        Initialize ToS Client.

        Args:
            ai_provider: AI provider to use ('openai', 'openrouter'). If None, uses AI_PROVIDER env var
            prompt_template_path: Path to prompt template file. If None, uses default from storage
            storage_client: Storage client instance. If None, creates one automatically
        """
        self.ai_provider = ai_provider or os.getenv("AI_PROVIDER", "openai")
        self.prompt_template_path = prompt_template_path
        self.storage_client = storage_client or get_storage_client()

        # Will be initialized when needed
        self._ai_client: Optional[AIClient] = None
        self._prompt_template: Optional[str] = None

        logger.info(f"Initialized ToS Client with AI provider: {self.ai_provider}")

    async def get_ai_client(self) -> AIClient:
        """Get or create AI client instance."""
        if self._ai_client is None:
            try:
                self._ai_client = get_llm_client(self.ai_provider)
                logger.info(f"Created AI client: {self.ai_provider}")
            except Exception as e:
                logger.error(f"Failed to create AI client: {e}")
                raise

        return self._ai_client

    async def get_prompt_template(self) -> str:
        """Load prompt template from storage or file."""
        if self._prompt_template is None:
            try:
                if self.prompt_template_path and Path(self.prompt_template_path).exists():
                    # Load from specified file path
                    with open(self.prompt_template_path, 'r', encoding='utf-8') as f:
                        self._prompt_template = f.read()
                    logger.info(f"Loaded prompt template from: {self.prompt_template_path}")
                else:
                    # Load from storage (default: data/prompt.txt)
                    try:
                        self._prompt_template = await self.storage_client.read_text("prompt.txt")
                        logger.info("Loaded prompt template from storage")
                    except Exception as e:
                        # Fallback to default template
                        self._prompt_template = self._get_default_template()
                        logger.warning(f"Could not load prompt from storage, using default: {e}")

            except Exception as e:
                logger.error(f"Failed to load prompt template: {e}")
                self._prompt_template = self._get_default_template()

        return self._prompt_template

    def _get_default_template(self) -> str:
        """Get default prompt template if none found."""
        return """
Please analyze the changes between these two versions of a Terms of Service document:

Document: {document_name}
Metadata: {metadata}

Previous Version:
{previous_content}

Current Version:
{current_content}

Please provide a comprehensive analysis including:

1. **Summary of Changes**: Brief overview of what changed
2. **New Terms**: Any completely new sections or policies
3. **Modified Terms**: Changes to existing terms and their implications
4. **Removed Terms**: Any sections that were removed
5. **User Impact**: How these changes might affect users
6. **Recommended Actions**: What users should know or do

Please be thorough but concise, focusing on meaningful changes that users should be aware of.
"""

    async def analyze_documents(
        self,
        previous_content: str,
        current_content: str,
        document_name: str,
        metadata: Dict[str, Any] = None,
        request_approval: bool = True
    ) -> Dict[str, Any]:
        """
        Analyze two ToS documents and optionally request user approval.

        Args:
            previous_content: Previous version of the document
            current_content: Current version of the document
            document_name: Name/identifier of the document
            metadata: Additional metadata about the documents
            request_approval: Whether to request user approval before sending

        Returns:
            Dict containing analysis results and metadata
        """
        logger.info(f"Starting analysis for document: {document_name}")

        # Get AI client and prompt template
        ai_client = await self.get_ai_client()
        prompt_template = await self.get_prompt_template()

        # Prepare metadata
        if metadata is None:
            metadata = {}

        metadata.update({
            "ai_provider": self.ai_provider,
            "analysis_timestamp": None,  # Will be set when analysis runs
            "document_name": document_name
        })

        # Show preview and request approval if needed
        if request_approval:
            approved = await self._request_approval(
                document_name=document_name,
                ai_provider=self.ai_provider,
                previous_length=len(previous_content),
                current_length=len(current_content),
                metadata=metadata
            )

            if not approved:
                return {
                    "status": "cancelled",
                    "message": "Analysis cancelled by user",
                    "document_name": document_name,
                    "metadata": metadata
                }

        # Perform analysis
        try:
            import datetime
            metadata["analysis_timestamp"] = datetime.datetime.utcnow().isoformat()

            logger.info(f"Sending analysis request to {self.ai_provider}")

            analysis_result = await ai_client.compare_documents(
                previous_content=previous_content,
                current_content=current_content,
                document_name=document_name,
                prompt_template=prompt_template,
                metadata=metadata
            )

            if analysis_result:
                result = {
                    "status": "success",
                    "analysis": analysis_result,
                    "document_name": document_name,
                    "metadata": metadata,
                    "ai_provider": self.ai_provider
                }

                logger.info(f"Analysis completed successfully for {document_name}")
                return result
            else:
                result = {
                    "status": "error",
                    "message": "AI analysis returned empty result",
                    "document_name": document_name,
                    "metadata": metadata
                }

                logger.error(f"AI analysis returned empty result for {document_name}")
                return result

        except Exception as e:
            result = {
                "status": "error",
                "message": f"Analysis failed: {str(e)}",
                "document_name": document_name,
                "metadata": metadata,
                "error": str(e)
            }

            logger.error(f"Analysis failed for {document_name}: {e}")
            return result

    async def _request_approval(
        self,
        document_name: str,
        ai_provider: str,
        previous_length: int,
        current_length: int,
        metadata: Dict[str, Any]
    ) -> bool:
        """
        Request user approval before performing analysis.

        Args:
            document_name: Name of the document
            ai_provider: AI provider being used
            previous_length: Length of previous document
            current_length: Length of current document
            metadata: Document metadata

        Returns:
            bool: True if user approves, False otherwise
        """
        print("\n" + "="*60)
        print("🔍 ToS Analysis Request")
        print("="*60)
        print(f"📄 Document: {document_name}")
        print(f"🤖 AI Provider: {ai_provider.title()}")
        print(f"📊 Document Size:")
        print(f"   Previous: {previous_length:,} characters")
        print(f"   Current:  {current_length:,} characters")
        print(f"   Change:   {current_length - previous_length:+,} characters")

        if metadata:
            print(f"📋 Metadata:")
            for key, value in metadata.items():
                if key not in ['analysis_timestamp']:
                    print(f"   {key}: {value}")

        print("\n💰 Note: This will consume AI API credits")
        print("="*60)

        while True:
            response = input("Proceed with analysis? [y/N]: ").strip().lower()

            if response in ['y', 'yes']:
                print("✅ Analysis approved")
                return True
            elif response in ['n', 'no', '']:
                print("❌ Analysis cancelled")
                return False
            else:
                print("Please enter 'y' for yes or 'n' for no")

    async def test_connection(self) -> bool:
        """Test connection to the AI service."""
        try:
            ai_client = await self.get_ai_client()
            return await ai_client.test_connection()
        except Exception as e:
            logger.error(f"Connection test failed: {e}")
            return False

    async def get_client_info(self) -> Dict[str, Any]:
        """Get information about the current AI client configuration."""
        try:
            ai_client = await self.get_ai_client()
            model_info = await ai_client.get_model_info()

            return {
                "ai_provider": self.ai_provider,
                "client_info": model_info,
                "prompt_template_source": self.prompt_template_path or "storage/prompt.txt",
                "storage_mode": getattr(self.storage_client, 'mode', 'unknown')
            }
        except Exception as e:
            return {
                "error": f"Failed to get client info: {e}",
                "ai_provider": self.ai_provider
            }

    def set_ai_provider(self, provider: str):
        """
        Change AI provider and reset client.

        Args:
            provider: New AI provider ('openai', 'openrouter')
        """
        if provider != self.ai_provider:
            self.ai_provider = provider
            self._ai_client = None  # Reset client to create new one
            logger.info(f"Switched AI provider to: {provider}")

    def set_prompt_template(self, template: Union[str, Path]):
        """
        Set custom prompt template.

        Args:
            template: Either template string content or path to template file
        """
        if isinstance(template, (str, Path)) and Path(template).exists():
            # It's a file path
            self.prompt_template_path = str(template)
            self._prompt_template = None  # Reset to reload from file
            logger.info(f"Set prompt template path: {template}")
        elif isinstance(template, str):
            # It's template content
            self._prompt_template = template
            self.prompt_template_path = None
            logger.info("Set prompt template content directly")
        else:
            raise ValueError("Template must be a string content or valid file path")


# Convenience function
def create_tos_client(
    ai_provider: str = None,
    prompt_template_path: str = None
) -> ToSClient:
    """
    Create a ToS client with specified configuration.

    Args:
        ai_provider: AI provider to use
        prompt_template_path: Path to prompt template file

    Returns:
        ToSClient: Configured ToS client instance
    """
    return ToSClient(
        ai_provider=ai_provider,
        prompt_template_path=prompt_template_path
    )