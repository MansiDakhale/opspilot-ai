"""
web_search.py — lightweight web search using DuckDuckGo (no API key required).

Falls back gracefully if the duckduckgo-search package is not installed.
"""

import logging
from typing import Optional

logger = logging.getLogger(__name__)


def web_search(query: str, max_results: int = 5) -> Optional[str]:
    """
    Search the live web using DuckDuckGo and return a formatted string
    of the top results.

    Returns:
        Formatted string of results, or None if the search failed.
    """
    try:
        from duckduckgo_search import DDGS
    except ImportError:
        logger.error(
            "duckduckgo-search is not installed. "
            "Add 'duckduckgo-search' to requirements.txt."
        )
        return None

    try:
        results = []

        with DDGS() as ddgs:
            for r in ddgs.text(query, max_results=max_results):
                title = r.get("title", "No title")
                href  = r.get("href",  "No URL")
                body  = r.get("body",  "No snippet")
                results.append(f"**{title}**\n{href}\n{body}")

        if not results:
            return "No web results found for this query."

        return "\n\n---\n\n".join(results)

    except Exception as exc:
        logger.error("DuckDuckGo search failed for query=%r: %s", query, exc)
        return f"Web search failed: {exc}"
