import logging
import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

def scrape_webpage(url: str) -> str:
    """
    Fetches a webpage and extracts the readable text content.
    """
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        
        logger.info(f"Navigating to {url}")
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        
        # Use BeautifulSoup to extract clean text
        soup = BeautifulSoup(response.text, "html.parser")
        
        # Remove scripts, styles, and hidden elements
        for element in soup(["script", "style", "nav", "footer", "header", "noscript"]):
            element.decompose()
            
        text = soup.get_text(separator="\n", strip=True)
        
        # Truncate to avoid context window explosion
        return text[:10000]
            
    except Exception as e:
        logger.error(f"Scraping failed: {e}")
        return f"Failed to scrape {url}. Error: {str(e)}"
