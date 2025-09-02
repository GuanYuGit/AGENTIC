"""
Web Fetcher tool using decorator pattern.
"""

import hashlib
import requests
from datetime import datetime
from typing import Dict, Any
from bs4 import BeautifulSoup

from decorators import tool, input_schema


@tool(
    name="WebFetcher",
    description="Fetches and parses HTML content from web URLs with comprehensive metadata extraction"
)
class WebFetcher:
    """Professional web content fetcher with robust error handling and metadata extraction"""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        })
        self.execution_count = 0
        self.last_execution = None
    
    @input_schema(
        url={"type": "string", "required": True, "description": "URL to fetch HTML content from"},
        timeout={"type": "integer", "default": 10, "description": "Request timeout in seconds"},
        follow_redirects={"type": "boolean", "default": True, "description": "Whether to follow HTTP redirects"}
    )
    def execute(self, url: str, timeout: int = 10, follow_redirects: bool = True) -> Dict[str, Any]:
        """
        Fetch HTML content from URL with comprehensive parsing
        
        Args:
            url: URL to fetch
            timeout: Request timeout in seconds
            follow_redirects: Whether to follow HTTP redirects
            
        Returns:
            Dict containing HTML content, parsed soup, and comprehensive metadata
        """
        self._log_execution()
        
        try:
            response = self.session.get(url, timeout=timeout, allow_redirects=follow_redirects)
            response.raise_for_status()
            
            # Generate content hash
            content_hash = hashlib.sha256(response.content).hexdigest()
            
            # Parse HTML with BeautifulSoup
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Extract comprehensive metadata
            metadata = self._extract_page_metadata(soup, response)
            
            return {
                "success": True,
                "url": url,
                "final_url": response.url,
                "html_content": response.text,
                "soup": soup,
                "title": metadata["title"],
                "description": metadata["description"],
                "page_metadata": metadata,
                "fetch_metadata": {
                    "retrieved_at": datetime.utcnow().isoformat() + "Z",
                    "content_type": response.headers.get('content-type', ''),
                    "http_status": response.status_code,
                    "content_hash": f"sha256:{content_hash}",
                    "content_length": len(response.text),
                    "response_headers": dict(response.headers),
                    "redirected": response.url != url
                }
            }
            
        except requests.exceptions.RequestException as e:
            return self._create_error_response(url, f"HTTP request failed: {str(e)}")
        except Exception as e:
            return self._create_error_response(url, f"Unexpected error: {str(e)}")
    
    def _extract_page_metadata(self, soup: BeautifulSoup, response) -> Dict[str, Any]:
        """Extract comprehensive page metadata"""
        # Title extraction
        title_tag = soup.find('title')
        title = title_tag.get_text(strip=True) if title_tag else "Untitled"
        
        # Meta description
        meta_desc = soup.find('meta', attrs={'name': 'description'})
        description = meta_desc.get('content', '') if meta_desc else ''
        
        # Open Graph metadata
        og_title = soup.find('meta', attrs={'property': 'og:title'})
        og_desc = soup.find('meta', attrs={'property': 'og:description'})
        og_image = soup.find('meta', attrs={'property': 'og:image'})
        og_type = soup.find('meta', attrs={'property': 'og:type'})
        
        # Twitter Card metadata
        twitter_title = soup.find('meta', attrs={'name': 'twitter:title'})
        twitter_desc = soup.find('meta', attrs={'name': 'twitter:description'})
        twitter_image = soup.find('meta', attrs={'name': 'twitter:image'})
        
        # Author information
        author_meta = soup.find('meta', attrs={'name': 'author'})
        
        # Publication date
        published_meta = soup.find('meta', attrs={'name': 'article:published_time'}) or \
                        soup.find('meta', attrs={'property': 'article:published_time'})
        
        # Language
        html_tag = soup.find('html')
        language = html_tag.get('lang', 'en') if html_tag else 'en'
        
        return {
            "title": title,
            "description": description,
            "language": language,
            "author": author_meta.get('content', '') if author_meta else '',
            "published_time": published_meta.get('content', '') if published_meta else '',
            "open_graph": {
                "title": og_title.get('content', '') if og_title else '',
                "description": og_desc.get('content', '') if og_desc else '',
                "image": og_image.get('content', '') if og_image else '',
                "type": og_type.get('content', '') if og_type else ''
            },
            "twitter_card": {
                "title": twitter_title.get('content', '') if twitter_title else '',
                "description": twitter_desc.get('content', '') if twitter_desc else '',
                "image": twitter_image.get('content', '') if twitter_image else ''
            }
        }
    
    def _create_error_response(self, url: str, error_message: str) -> Dict[str, Any]:
        """Create standardized error response"""
        return {
            "success": False,
            "url": url,
            "error": error_message,
            "fetch_metadata": {
                "retrieved_at": datetime.utcnow().isoformat() + "Z",
                "error": error_message
            }
        }
    
    def _log_execution(self):
        """Log tool execution for debugging"""
        self.execution_count += 1
        self.last_execution = datetime.utcnow().isoformat() + "Z"
    
    def get_metadata(self) -> Dict[str, Any]:
        """Get tool metadata and statistics"""
        return {
            "name": self._tool_name,
            "description": self._tool_description,
            "execution_count": self.execution_count,
            "last_execution": self.last_execution
        }