"""
HTML formatting utilities for converting markdown analysis to HTML.
"""

import re


def markdown_to_html(markdown_text: str) -> str:
    """
    Convert basic markdown formatting to HTML.

    Args:
        markdown_text: Text with markdown formatting

    Returns:
        HTML formatted text
    """
    if not markdown_text:
        return ""

    html = markdown_text

    # Convert headers (## Header -> <h2>Header</h2>)
    html = re.sub(r'^### (.+)$', r'<h3>\1</h3>', html, flags=re.MULTILINE)
    html = re.sub(r'^## (.+)$', r'<h2>\1</h2>', html, flags=re.MULTILINE)
    html = re.sub(r'^# (.+)$', r'<h1>\1</h1>', html, flags=re.MULTILINE)

    # Convert bold text (**text** -> <strong>text</strong>)
    html = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', html)

    # Convert italic text (*text* -> <em>text</em>)
    html = re.sub(r'\*(.+?)\*', r'<em>\1</em>', html)

    # Convert numbered lists (1. item -> <ol><li>item</li></ol>)
    lines = html.split('\n')
    processed_lines = []
    in_ol = False
    in_ul = False

    i = 0
    while i < len(lines):
        line = lines[i].strip()

        # Handle numbered lists
        if re.match(r'^\d+\.\s+', line):
            if not in_ol:
                if in_ul:
                    processed_lines.append('</ul>')
                    in_ul = False
                processed_lines.append('<ol>')
                in_ol = True

            item_text = re.sub(r'^\d+\.\s+', '', line)
            processed_lines.append(f'<li>{item_text}</li>')

        # Handle bullet lists
        elif re.match(r'^[-*]\s+', line):
            if not in_ul:
                if in_ol:
                    processed_lines.append('</ol>')
                    in_ol = False
                processed_lines.append('<ul>')
                in_ul = True

            item_text = re.sub(r'^[-*]\s+', '', line)
            processed_lines.append(f'<li>{item_text}</li>')

        # Regular line
        else:
            # Close any open lists
            if in_ol:
                processed_lines.append('</ol>')
                in_ol = False
            if in_ul:
                processed_lines.append('</ul>')
                in_ul = False

            # Add line (convert to paragraph if not empty and not a header)
            if line and not line.startswith('<h'):
                processed_lines.append(f'<p>{line}</p>')
            elif line.startswith('<h'):
                processed_lines.append(line)
            # Skip empty lines - they will create natural spacing

        i += 1

    # Close any remaining open lists
    if in_ol:
        processed_lines.append('</ol>')
    if in_ul:
        processed_lines.append('</ul>')

    # Join lines and clean up
    html = '\n'.join(processed_lines)

    # Clean up empty paragraphs
    html = re.sub(r'<p>\s*</p>', '', html)

    # Remove any stray breaks
    html = re.sub(r'<br>\s*<br>', '', html)

    return html.strip()