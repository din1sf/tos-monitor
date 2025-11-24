"""
HTML parser utility for ToS Monitor.
Handles web scraping and HTML content extraction with error handling and retries.
"""

import asyncio
import logging
import re
from typing import Optional, Dict, Any
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup


logger = logging.getLogger(__name__)


class HTMLParser:
    """
    HTML parser for fetching and extracting content from web pages.
    Includes user-agent spoofing, timeout handling, and content extraction.
    """

    def __init__(self, timeout: int = 30, max_retries: int = 3):
        """
        Initialize HTML parser.

        Args:
            timeout: Request timeout in seconds
            max_retries: Maximum number of retry attempts
        """
        self.timeout = timeout
        self.max_retries = max_retries

        # User agents for different scenarios
        self.user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:89.0) Gecko/20100101 Firefox/89.0"
        ]

        self.session = requests.Session()
        self.session.headers.update({
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Accept-Encoding": "gzip, deflate",
            "DNT": "1",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1"
        })

    async def fetch_page(self, url: str, selector: Optional[str] = None, user_agent_index: int = 0) -> Optional[Dict[str, Any]]:
        """
        Fetch and parse a web page.

        Args:
            url: URL to fetch
            selector: CSS selector to extract specific content (optional)
            user_agent_index: Index of user agent to use

        Returns:
            Optional[Dict[str, Any]]: Dictionary with 'content', 'title', 'url' and 'metadata'
        """
        for attempt in range(self.max_retries):
            try:
                # Set user agent for this attempt
                user_agent = self.user_agents[user_agent_index % len(self.user_agents)]
                self.session.headers["User-Agent"] = user_agent

                logger.info(f"Fetching {url} (attempt {attempt + 1}/{self.max_retries})")

                # Make the request
                response = self.session.get(url, timeout=self.timeout)
                response.raise_for_status()

                # Check content type
                content_type = response.headers.get("content-type", "").lower()
                if "html" not in content_type:
                    logger.warning(f"Non-HTML content type: {content_type}")

                # Parse HTML
                soup = BeautifulSoup(response.content, "html.parser")

                # Extract content
                content = self._extract_content(soup, selector)
                title = self._extract_title(soup)

                # Extract metadata
                metadata = self._extract_metadata(soup, response)

                result = {
                    "content": content,
                    "title": title,
                    "url": url,
                    "metadata": metadata
                }

                logger.info(f"Successfully fetched {url} ({len(content)} characters)")
                return result

            except requests.exceptions.RequestException as e:
                logger.warning(f"Request failed for {url} (attempt {attempt + 1}): {str(e)}")
                if attempt < self.max_retries - 1:
                    # Wait before retry with exponential backoff
                    wait_time = 2 ** attempt
                    logger.info(f"Waiting {wait_time} seconds before retry...")
                    await asyncio.sleep(wait_time)
                else:
                    logger.error(f"All attempts failed for {url}")

            except Exception as e:
                logger.error(f"Unexpected error fetching {url}: {str(e)}")
                break

        return None

    def _extract_content(self, soup: BeautifulSoup, selector: Optional[str] = None) -> str:
        """
        Extract text content from HTML.

        Args:
            soup: BeautifulSoup object
            selector: CSS selector for specific content

        Returns:
            str: Extracted text content
        """
        try:
            if selector:
                # Use specific selector
                selected_elements = soup.select(selector)
                if selected_elements:
                    content = "\n\n".join(element.get_text(strip=True, separator="\n")
                                        for element in selected_elements)
                else:
                    logger.warning(f"Selector '{selector}' found no elements, falling back to full content")
                    content = self._extract_full_content(soup)
            else:
                content = self._extract_full_content(soup)

            # Clean up content
            content = self._clean_content(content)
            return content

        except Exception as e:
            logger.error(f"Error extracting content: {str(e)}")
            return ""

    def _extract_full_content(self, soup: BeautifulSoup) -> str:
        """
        Extract full page content, removing navigation and boilerplate.

        Args:
            soup: BeautifulSoup object

        Returns:
            str: Cleaned text content
        """
        # Remove unwanted elements
        unwanted_selectors = [
            "nav", "header", "footer", "aside", ".nav", ".navigation", ".menu",
            ".sidebar", ".advertisement", ".ad", ".ads", ".social", ".share",
            "script", "style", "noscript", ".cookie", ".popup", ".modal",
            ".breadcrumb", ".pagination", "#comments", ".comments"
        ]

        for selector in unwanted_selectors:
            for element in soup.select(selector):
                element.decompose()

        # Try to find main content areas first
        main_content_selectors = [
            "main", "article", ".main", ".content", ".main-content",
            ".article-content", ".post-content", "#main", "#content"
        ]

        for selector in main_content_selectors:
            main_elements = soup.select(selector)
            if main_elements:
                content = "\n\n".join(element.get_text(strip=True, separator="\n")
                                    for element in main_elements)
                if len(content.strip()) > 100:  # Only use if substantial content
                    return content

        # Fallback to body content
        body = soup.find("body")
        if body:
            return body.get_text(strip=True, separator="\n")
        else:
            return soup.get_text(strip=True, separator="\n")

    def _extract_title(self, soup: BeautifulSoup) -> str:
        """
        Extract page title.

        Args:
            soup: BeautifulSoup object

        Returns:
            str: Page title
        """
        # Try different title sources
        title_selectors = [
            "title",
            "h1",
            "meta[property='og:title']",
            "meta[name='title']"
        ]

        for selector in title_selectors:
            element = soup.select_one(selector)
            if element:
                if element.name == "meta":
                    title = element.get("content", "").strip()
                else:
                    title = element.get_text(strip=True)

                if title:
                    return title

        return "Untitled"

    def _extract_metadata(self, soup: BeautifulSoup, response: requests.Response) -> Dict[str, Any]:
        """
        Extract page metadata.

        Args:
            soup: BeautifulSoup object
            response: HTTP response object

        Returns:
            Dict[str, Any]: Page metadata
        """
        metadata = {
            "status_code": response.status_code,
            "content_type": response.headers.get("content-type", ""),
            "content_length": len(response.content),
            "encoding": response.encoding,
            "url": response.url
        }

        # Extract meta tags
        meta_tags = {}
        for meta in soup.find_all("meta"):
            name = meta.get("name") or meta.get("property")
            content = meta.get("content")
            if name and content:
                meta_tags[name] = content

        metadata["meta_tags"] = meta_tags

        # Extract language
        html_tag = soup.find("html")
        if html_tag and html_tag.get("lang"):
            metadata["language"] = html_tag.get("lang")

        return metadata

    def _clean_content(self, content: str) -> str:
        """
        Clean extracted content.

        Args:
            content: Raw extracted content

        Returns:
            str: Cleaned content
        """
        if not content:
            return ""

        # Normalize whitespace
        content = re.sub(r'\s+', ' ', content)
        content = re.sub(r'\n\s*\n', '\n\n', content)

        # Remove excessive newlines
        content = re.sub(r'\n{3,}', '\n\n', content)

        # Remove common boilerplate text patterns
        boilerplate_patterns = [
            r'Cookie Policy.*?Accept',
            r'This website uses cookies.*?(?=\n|$)',
            r'By continuing to use.*?(?=\n|$)',
            r'Subscribe to.*?newsletter.*?(?=\n|$)',
            r'Follow us on.*?(?=\n|$)',
            r'Share this.*?(?=\n|$)',
            r'Print this page.*?(?=\n|$)'
        ]

        for pattern in boilerplate_patterns:
            content = re.sub(pattern, '', content, flags=re.IGNORECASE | re.DOTALL)

        return content.strip()

    async def validate_url(self, url: str) -> bool:
        """
        Validate if a URL is accessible.

        Args:
            url: URL to validate

        Returns:
            bool: True if URL is accessible, False otherwise
        """
        try:
            response = self.session.head(url, timeout=self.timeout)
            return response.status_code < 400
        except Exception:
            return False

    def close(self):
        """Close the session."""
        self.session.close()


def get_html_parser() -> HTMLParser:
    """
    Get a configured HTML parser instance.

    Returns:
        HTMLParser: Configured HTML parser
    """
    return HTMLParser(timeout=30, max_retries=3)