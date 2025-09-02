"""
Image Extractor tool for extracting and processing images from HTML.
"""

import hashlib
from typing import Dict, Any, List
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse

from .base_tool import BaseTool


class ImageExtractor(BaseTool):
    """Tool for extracting and filtering image content from HTML"""
    
    def __init__(self):
        super().__init__(
            name="ImageExtractor",
            description="Extracts image information from HTML with basic semantic filtering"
        )
    
    def execute(self, soup: BeautifulSoup, base_url: str) -> Dict[str, Any]:
        """
        Extract images from parsed HTML
        
        Args:
            soup: BeautifulSoup parsed HTML
            base_url: Base URL for resolving relative URLs
            
        Returns:
            Dict containing extracted images and metadata
        """
        self._log_execution()
        
        try:
            # Get domain for company logo detection
            domain = urlparse(base_url).netloc.lower()
            company_name = domain.split('.')[-2] if '.' in domain else domain
            
            images = []
            img_tags = soup.find_all('img')
            
            for i, img in enumerate(img_tags):
                src = img.get('src')
                if not src:
                    continue
                
                # Skip obvious data URIs and tiny images
                if src.startswith('data:') or 'base64' in src:
                    continue
                
                # Convert relative URLs to absolute
                src = self._normalize_url(src, base_url)
                alt = img.get('alt', '')
                
                # Skip images with company branding in alt text
                if company_name and company_name in alt.lower():
                    continue
                
                # Skip obvious tracking/analytics images
                if any(tracker in src.lower() for tracker in ['analytics', 'tracking', 'pixel', 'beacon']):
                    continue
                
                # Get enhanced context text
                context = self._get_image_context(img)
                
                # Check if image is in header/footer/nav areas
                nav_parent = img.find_parent(['header', 'footer', 'nav', 'aside'])
                is_navigation = nav_parent is not None
                
                # Create image record
                image_data = {
                    "id": f"img_{i+1:02d}",
                    "src": src,
                    "alt": alt,
                    "context_text": context,
                    "width": img.get('width'),
                    "height": img.get('height'),
                    "is_navigation": is_navigation,
                    "company_domain": domain,
                    "basic_score": 0.0,  # Will be calculated by ContentFilter
                    "extraction_metadata": {
                        "parent_tag": img.parent.name if img.parent else None,
                        "has_alt": bool(alt),
                        "in_figure": bool(img.find_parent('figure')),
                        "in_article": bool(img.find_parent(['article', 'main']))
                    }
                }
                
                images.append(image_data)
            
            return {
                "success": True,
                "images": images,
                "extraction_metadata": {
                    "total_img_tags": len(img_tags),
                    "extracted_images": len(images),
                    "filtered_out": len(img_tags) - len(images),
                    "company_domain": domain
                }
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "images": []
            }
    
    def _normalize_url(self, src: str, base_url: str) -> str:
        """Convert relative URLs to absolute URLs"""
        if src.startswith('//'):
            return 'https:' + src
        elif src.startswith('/'):
            return urljoin(base_url, src)
        elif not src.startswith('http'):
            return urljoin(base_url, src)
        return src
    
    def _get_image_context(self, img) -> str:
        """Get context text around the image"""
        context = ""
        parent = img.parent
        
        if parent:
            # Look for caption, figure, or article context
            figure_parent = parent.find_parent(['figure', 'article', 'section'])
            if figure_parent:
                context = figure_parent.get_text(strip=True)[:200]
            else:
                context = parent.get_text(strip=True)[:100]
        
        return context
    
    def _get_input_schema(self) -> Dict[str, Any]:
        """Define input schema for Strands SDK"""
        return {
            "type": "object",
            "properties": {
                "soup": {
                    "description": "BeautifulSoup parsed HTML object"
                },
                "base_url": {
                    "type": "string",
                    "description": "Base URL for resolving relative image URLs"
                }
            },
            "required": ["soup", "base_url"]
        }