import json
import logging
import requests

logger = logging.getLogger(__name__)

def execute_api_request(method: str, url: str, headers: dict = None, body: dict = None) -> str:
    """
    Executes an HTTP request to an external API.
    """
    try:
        if method.upper() == "GET":
            response = requests.get(url, headers=headers, timeout=10)
        elif method.upper() == "POST":
            response = requests.post(url, headers=headers, json=body, timeout=10)
        else:
            return f"Unsupported HTTP method: {method}"

        response.raise_for_status()

        # Try to return pretty-printed JSON if possible
        try:
            return json.dumps(response.json(), indent=2)
        except json.JSONDecodeError:
            return response.text[:2000]  # truncate raw text to avoid overflowing context
            
    except requests.exceptions.RequestException as e:
        logger.error(f"API Request failed: {e}")
        return f"API Request to {url} failed: {e}"
