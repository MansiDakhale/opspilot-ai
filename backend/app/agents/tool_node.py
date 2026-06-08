"""
tool_node.py — routes 'tools' queries to the appropriate tool
and formats results for the LLM summariser.
"""

import logging
import re

from app.agents.tools.web_search import web_search
from app.agents.tools.ops_tools  import (
    check_docker_status,
    check_endpoint_health,
    get_system_usage,
)
from app.agents.tools.api_agent import execute_api_request
from app.agents.tools.browser_agent import scrape_webpage
from app.services.llm_service import generate_response

logger = logging.getLogger(__name__)


_TOOL_SELECTOR_PROMPT = """You are a tool selector. Choose the RIGHT tool for the user's query.

Available tools:
  web_search      - Search the internet for real-time or current information
  docker_status   - Show running Docker containers
  system_usage    - Show CPU / RAM / disk usage on this server
  endpoint_health - Check if a specific HTTP endpoint/URL is up
  browser_scrape  - Navigate to a URL and scrape its readable text content
  api_request     - Make an HTTP GET/POST request to an API endpoint

Respond with ONLY the tool name, nothing else.
If the query is about checking an endpoint health, respond with: endpoint_health <url>
If the query is about scraping/reading a website, respond with: browser_scrape <url>
If the query is about making an API call, respond with: api_request <method> <url>

User query: {query}"""


def tool_node(state: dict) -> dict:
    """
    Decide which tool to use, execute it, and store results in state.
    The summarizer_node will then synthesize a natural-language response.
    """
    query = state["query"]

    # Ask the LLM to pick the right tool
    try:
        tool_choice = generate_response(
            _TOOL_SELECTOR_PROMPT.format(query=query),
            model=state.get("model")
        ).strip()
    except Exception as exc:
        logger.error("Tool selector failed: %s", exc)
        tool_choice = "web_search"

    logger.info("Tool executor: query=%r → tool=%r", query, tool_choice)
    tool_name = tool_choice.split()[0].lower()

    # Execute the selected tool
    if tool_name == "endpoint_health":
        # Extract URL from the choice string
        match = re.search(r"https?://\S+", tool_choice)
        url   = match.group(0) if match else query
        result = check_endpoint_health(url)

    elif tool_name == "browser_scrape":
        match = re.search(r"https?://\S+", tool_choice)
        url   = match.group(0) if match else query
        result = scrape_webpage(url)
        
    elif tool_name == "api_request":
        parts = tool_choice.split()
        method = parts[1].upper() if len(parts) > 1 else "GET"
        match = re.search(r"https?://\S+", tool_choice)
        url   = match.group(0) if match else query
        result = execute_api_request(method, url)

    elif tool_name == "docker_status":
        result = check_docker_status()

    elif tool_name == "system_usage":
        result = get_system_usage()

    else:
        # Default to web search
        result = web_search(query) or "Web search returned no results."

    return {
        **state,
        "tool_results": result,
    }
