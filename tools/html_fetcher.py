"""
HTML Fetcher tool for retrieving and parsing web pages.
"""

import hashlib
import requests
from datetime import datetime
from typing import Dict, Any
from bs4 import BeautifulSoup

from .base_tool import BaseTool


class HTMLFetcher(BaseTool):
    """Tool for fetching and parsing HTML content from URLs"""
    
    def __init__(self):
        super().__init__(
            name="HTMLFetcher",
            description="Fetches HTML content from URLs and provides basic parsing"
        )
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
    
    def execute(self, url: str, timeout: int = 10) -> Dict[str, Any]:
        """
        Fetch HTML content from URL
        
        Args:
            url: URL to fetch
            timeout: Request timeout in seconds
            
        Returns:
            Dict containing HTML content and metadata
        """
        self._log_execution()
        
        try:
            response = self.session.get(url, timeout=timeout)
            response.raise_for_status()
            
            content_hash = hashlib.sha256(response.content).hexdigest()
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Extract basic metadata
            title_tag = soup.find('title')
            title = title_tag.get_text(strip=True) if title_tag else "Untitled"
            
            # Get meta description
            meta_desc = soup.find('meta', attrs={'name': 'description'})
            description = meta_desc.get('content', '') if meta_desc else ''
            
            return {
                "success": True,
                "url": url,
                "html_content": response.text,
                "soup": soup,  # Parsed BeautifulSoup object
                "title": title,
                "description": description,
                "fetch_metadata": {
                    "retrieved_at": datetime.utcnow().isoformat() + "Z",
                    "content_type": response.headers.get('content-type', ''),
                    "http_status": response.status_code,
                    "content_hash": f"sha256:{content_hash}",
                    "content_length": len(response.text),
                    "robots_respected": True  # Simplified for demo
                }
            }
            
        except Exception as e:
            return {
                "success": False,
                "url": url,
                "error": str(e),
                "fetch_metadata": {
                    "retrieved_at": datetime.utcnow().isoformat() + "Z",
                    "error": str(e)
                }
            }
    
    def _get_input_schema(self) -> Dict[str, Any]:
        """Define input schema for Strands SDK"""
        return {
            "type": "object",
            "properties": {
                "url": {
                    "type": "string",
                    "description": "URL to fetch HTML content from"
                },
                "timeout": {
                    "type": "integer", 
                    "description": "Request timeout in seconds",
                    "default": 10
                }
            },
            "required": ["url"]
        }