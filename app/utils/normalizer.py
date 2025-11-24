"""
Text normalizer utility for ToS Monitor.
Handles text normalization, cleaning, and standardization for consistent comparison.
"""

import re
import logging
from typing import List, Dict, Any
from datetime import datetime


logger = logging.getLogger(__name__)


class TextNormalizer:
    """
    Text normalizer for cleaning and standardizing document content.
    Removes boilerplate, normalizes formatting, and preserves meaningful structure.
    """

    def __init__(self):
        """Initialize text normalizer with default patterns."""
        # Patterns for common boilerplate content
        self.boilerplate_patterns = [
            # Navigation and UI elements
            r'(?i)skip\s+to\s+(?:main\s+)?content',
            r'(?i)table\s+of\s+contents?',
            r'(?i)jump\s+to\s+(?:navigation|section)',
            r'(?i)breadcrumb(?:s)?',
            r'(?i)you\s+are\s+here:?',

            # Social media and sharing
            r'(?i)share\s+(?:this\s+)?(?:on|via)\s+(?:facebook|twitter|linkedin|social|media)',
            r'(?i)follow\s+us\s+on\s+(?:facebook|twitter|linkedin|instagram)',
            r'(?i)like\s+us\s+on\s+facebook',
            r'(?i)tweet\s+this',
            r'(?i)share\s+this\s+(?:page|article|post)',

            # Email and subscriptions
            r'(?i)subscribe\s+to\s+(?:our\s+)?newsletter',
            r'(?i)sign\s+up\s+for\s+(?:updates|alerts|newsletter)',
            r'(?i)email\s+(?:updates|alerts|subscription)',
            r'(?i)unsubscribe\s+(?:from\s+)?(?:this\s+)?(?:list|newsletter)',

            # Cookie and privacy notices
            r'(?i)this\s+(?:website|site)\s+uses\s+cookies',
            r'(?i)by\s+(?:continuing|using|browsing)\s+(?:this\s+)?(?:site|website)',
            r'(?i)cookie\s+(?:policy|notice|banner|consent)',
            r'(?i)accept\s+(?:all\s+)?cookies?',
            r'(?i)manage\s+cookie\s+(?:preferences|settings)',

            # Print and download
            r'(?i)print\s+(?:this\s+)?(?:page|document|article)',
            r'(?i)download\s+(?:as\s+)?(?:pdf|word|doc)',
            r'(?i)save\s+(?:as\s+)?(?:pdf|bookmark)',

            # Advertisement indicators
            r'(?i)advertisement',
            r'(?i)sponsored\s+(?:content|by|post)',
            r'(?i)ads?\s+by\s+google',

            # Language and accessibility
            r'(?i)change\s+language',
            r'(?i)select\s+language',
            r'(?i)accessibility\s+(?:options|settings)',
            r'(?i)text\s+size',
            r'(?i)high\s+contrast',

            # Common footer content
            r'(?i)copyright\s+©?\s*\d{4}',
            r'(?i)all\s+rights\s+reserved',
            r'(?i)privacy\s+policy\s*\|\s*terms\s+of\s+(?:service|use)',
            r'(?i)contact\s+us\s*\|\s*about\s+us',

            # Loading and error messages
            r'(?i)loading\.{3,}',
            r'(?i)please\s+(?:wait|enable\s+javascript)',
            r'(?i)javascript\s+(?:is\s+)?(?:required|disabled)',
            r'(?i)this\s+(?:page|content)\s+requires\s+javascript'
        ]

        # Patterns for dates and timestamps (to normalize)
        self.date_patterns = [
            # Various date formats
            r'\b(?:last\s+)?(?:updated|modified|revised)\s*:?\s*(?:on\s+)?'
            r'(?:january|february|march|april|may|june|july|august|september|october|november|december)'
            r'\s+\d{1,2},?\s+\d{4}',

            r'\b(?:last\s+)?(?:updated|modified|revised)\s*:?\s*(?:on\s+)?'
            r'(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)'
            r'\.?\s+\d{1,2},?\s+\d{4}',

            r'\b(?:last\s+)?(?:updated|modified|revised)\s*:?\s*(?:on\s+)?'
            r'\d{1,2}[\/\-\.]\d{1,2}[\/\-\.]\d{2,4}',

            r'\b(?:last\s+)?(?:updated|modified|revised)\s*:?\s*(?:on\s+)?'
            r'\d{4}[\/\-\.]\d{1,2}[\/\-\.]\d{1,2}',

            # Version numbers
            r'\bversion\s+\d+(?:\.\d+)*',
            r'\bv\d+(?:\.\d+)*',

            # Effective dates (preserve these as they're important)
            r'\beffective\s+(?:date\s*:?\s*)?'
            r'(?:january|february|march|april|may|june|july|august|september|october|november|december)'
            r'\s+\d{1,2},?\s+\d{4}',
        ]

        # Section headers to preserve
        self.important_headers = [
            r'(?i)\b(?:introduction|overview|summary)\b',
            r'(?i)\b(?:definitions|definitions\s+and\s+terms)\b',
            r'(?i)\b(?:acceptance|acceptance\s+of\s+terms)\b',
            r'(?i)\b(?:modifications|changes|amendments)\b',
            r'(?i)\b(?:privacy|privacy\s+policy)\b',
            r'(?i)\b(?:data|data\s+(?:protection|privacy|use))\b',
            r'(?i)\b(?:liability|limitation\s+of\s+liability)\b',
            r'(?i)\b(?:warranties|disclaimers?)\b',
            r'(?i)\b(?:termination|suspension)\b',
            r'(?i)\b(?:governing\s+law|jurisdiction)\b',
            r'(?i)\b(?:dispute\s+resolution|arbitration)\b',
            r'(?i)\b(?:intellectual\s+property|copyright)\b',
            r'(?i)\b(?:user\s+(?:conduct|obligations|responsibilities))\b',
            r'(?i)\b(?:prohibited\s+(?:uses?|activities|conduct))\b',
            r'(?i)\b(?:payment|billing|fees)\b',
            r'(?i)\b(?:refunds?|cancellation)\b',
            r'(?i)\b(?:third\s+part(?:y|ies))\b',
            r'(?i)\b(?:cookies?|tracking)\b',
            r'(?i)\b(?:contact|support)\b'
        ]

    def normalize_text(self, text: str, preserve_structure: bool = True) -> str:
        """
        Normalize text content for consistent comparison.

        Args:
            text: Input text to normalize
            preserve_structure: Whether to preserve document structure (headings, lists)

        Returns:
            str: Normalized text
        """
        if not text:
            return ""

        logger.debug(f"Normalizing text ({len(text)} characters)")

        # Step 1: Basic cleaning
        text = self._basic_cleanup(text)

        # Step 2: Remove boilerplate content
        text = self._remove_boilerplate(text)

        # Step 3: Normalize dates and versions (but preserve effective dates)
        text = self._normalize_dates(text)

        # Step 4: Standardize whitespace and formatting
        text = self._standardize_formatting(text)

        # Step 5: Preserve or normalize structure
        if preserve_structure:
            text = self._preserve_structure(text)
        else:
            text = self._flatten_structure(text)

        # Step 6: Final cleanup
        text = self._final_cleanup(text)

        logger.debug(f"Normalized text ({len(text)} characters)")
        return text.strip()

    def _basic_cleanup(self, text: str) -> str:
        """Perform basic text cleanup."""
        # Remove excessive whitespace
        text = re.sub(r'\s+', ' ', text)

        # Remove zero-width characters and other unicode oddities
        text = re.sub(r'[\u200b\u200c\u200d\ufeff]', '', text)

        # Normalize quotes
        text = re.sub(r'["""]', '"', text)
        text = re.sub(r'['']', "'", text)

        # Normalize dashes
        text = re.sub(r'[–—]', '-', text)

        # Remove excessive punctuation
        text = re.sub(r'\.{4,}', '...', text)
        text = re.sub(r'-{3,}', '---', text)

        return text

    def _remove_boilerplate(self, text: str) -> str:
        """Remove common boilerplate content."""
        for pattern in self.boilerplate_patterns:
            text = re.sub(pattern, '', text, flags=re.IGNORECASE | re.MULTILINE)

        # Remove standalone single characters and short meaningless phrases
        lines = text.split('\n')
        filtered_lines = []

        for line in lines:
            line = line.strip()
            # Skip very short lines that are likely navigation/boilerplate
            if len(line) < 3:
                continue
            # Skip lines with only punctuation/symbols
            if re.match(r'^[^\w\s]*$', line):
                continue
            # Skip common navigation words
            if line.lower() in ['home', 'menu', 'back', 'next', 'previous', 'top', 'skip']:
                continue

            filtered_lines.append(line)

        return '\n'.join(filtered_lines)

    def _normalize_dates(self, text: str) -> str:
        """Normalize dates while preserving effective dates."""
        # First, protect effective dates (these are important for legal documents)
        effective_dates = []
        effective_pattern = r'(effective\s+(?:date\s*:?\s*)?(?:january|february|march|april|may|june|july|august|september|october|november|december)\s+\d{1,2},?\s+\d{4})'

        def protect_effective_date(match):
            effective_dates.append(match.group(1))
            return f"__EFFECTIVE_DATE_{len(effective_dates)-1}__"

        text = re.sub(effective_pattern, protect_effective_date, text, flags=re.IGNORECASE)

        # Now normalize other dates
        for pattern in self.date_patterns:
            text = re.sub(pattern, '[DATE_NORMALIZED]', text, flags=re.IGNORECASE)

        # Restore effective dates
        for i, date in enumerate(effective_dates):
            text = text.replace(f"__EFFECTIVE_DATE_{i}__", date)

        return text

    def _standardize_formatting(self, text: str) -> str:
        """Standardize text formatting."""
        # Normalize line breaks
        text = re.sub(r'\r\n?', '\n', text)

        # Remove excessive newlines but preserve paragraph structure
        text = re.sub(r'\n\s*\n\s*\n+', '\n\n', text)

        # Standardize bullet points
        text = re.sub(r'^[-•·▪▫‣⁃]\s*', '• ', text, flags=re.MULTILINE)

        # Standardize numbered lists
        text = re.sub(r'^\d+\.\s*', lambda m: f"{m.group().strip()} ", text, flags=re.MULTILINE)

        # Remove trailing whitespace from lines
        lines = [line.rstrip() for line in text.split('\n')]
        text = '\n'.join(lines)

        return text

    def _preserve_structure(self, text: str) -> str:
        """Preserve document structure while normalizing."""
        lines = text.split('\n')
        structured_lines = []

        for line in lines:
            line = line.strip()
            if not line:
                structured_lines.append('')
                continue

            # Identify and preserve headers
            if self._is_important_header(line):
                # Normalize header formatting
                line = line.upper() if len(line) < 50 else line.title()
                structured_lines.append(f"\n{line}\n")
            elif self._is_list_item(line):
                # Preserve list formatting
                structured_lines.append(line)
            else:
                # Regular paragraph text
                structured_lines.append(line)

        return '\n'.join(structured_lines)

    def _flatten_structure(self, text: str) -> str:
        """Flatten document structure for plain text comparison."""
        # Remove multiple newlines
        text = re.sub(r'\n+', ' ', text)

        # Remove excessive spaces
        text = re.sub(r'\s+', ' ', text)

        return text

    def _is_important_header(self, line: str) -> bool:
        """Check if a line is an important section header."""
        if len(line) > 100:  # Too long to be a header
            return False

        # Check against important header patterns
        for pattern in self.important_headers:
            if re.search(pattern, line):
                return True

        # Check for header-like formatting
        if re.match(r'^[A-Z][A-Z\s\d\.\-]{5,50}$', line):  # ALL CAPS headers
            return True

        if re.match(r'^\d+\.\s*[A-Z][A-Za-z\s]{5,50}$', line):  # Numbered headers
            return True

        return False

    def _is_list_item(self, line: str) -> bool:
        """Check if a line is a list item."""
        return bool(re.match(r'^(?:•|\d+\.|\([a-z]\))\s+', line))

    def _final_cleanup(self, text: str) -> str:
        """Perform final cleanup of normalized text."""
        # Remove multiple spaces
        text = re.sub(r' +', ' ', text)

        # Remove space before punctuation
        text = re.sub(r' +([,.;:!?])', r'\1', text)

        # Ensure proper spacing after punctuation
        text = re.sub(r'([,.;:!?])([A-Za-z])', r'\1 \2', text)

        # Remove excessive newlines at start/end
        text = text.strip()

        # Ensure consistent paragraph separation
        text = re.sub(r'\n\s*\n', '\n\n', text)

        return text

    def get_content_fingerprint(self, text: str) -> str:
        """
        Create a fingerprint of the text content for quick comparison.
        Removes dynamic elements like dates and focuses on substantial content.

        Args:
            text: Input text

        Returns:
            str: Content fingerprint
        """
        # Normalize for fingerprinting (more aggressive)
        fingerprint_text = self.normalize_text(text, preserve_structure=False)

        # Remove all dates and numbers that might change
        fingerprint_text = re.sub(r'\b\d+\b', '[NUM]', fingerprint_text)

        # Remove special characters
        fingerprint_text = re.sub(r'[^\w\s]', '', fingerprint_text)

        # Normalize case
        fingerprint_text = fingerprint_text.lower()

        # Remove extra whitespace
        fingerprint_text = ' '.join(fingerprint_text.split())

        return fingerprint_text

    def extract_sections(self, text: str) -> Dict[str, str]:
        """
        Extract major sections from legal document.

        Args:
            text: Document text

        Returns:
            Dict[str, str]: Dictionary of section names to content
        """
        sections = {}
        lines = text.split('\n')
        current_section = "Introduction"
        current_content = []

        for line in lines:
            line = line.strip()
            if not line:
                continue

            # Check if this is a section header
            if self._is_important_header(line):
                # Save previous section
                if current_content:
                    sections[current_section] = '\n'.join(current_content).strip()

                # Start new section
                current_section = line
                current_content = []
            else:
                current_content.append(line)

        # Save last section
        if current_content:
            sections[current_section] = '\n'.join(current_content).strip()

        return sections


def get_text_normalizer() -> TextNormalizer:
    """
    Get a configured text normalizer instance.

    Returns:
        TextNormalizer: Configured text normalizer
    """
    return TextNormalizer()