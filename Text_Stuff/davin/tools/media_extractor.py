"""
Media Extractor tool using decorator pattern.
"""

import hashlib
from typing import Dict, Any, List
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse

from decorators import tool, input_schema


@tool(
    name="MediaExtractor", 
    description="Extracts and analyzes media content (images, videos) from HTML with intelligent filtering"
)
class MediaExtractor:
    """Advanced media extraction engine with semantic filtering and quality analysis"""
    
    def __init__(self):
        self.execution_count = 0
        self.last_execution = None
    
    @input_schema(
        soup={"description": "BeautifulSoup parsed HTML object", "required": True},
        base_url={"type": "string", "description": "Base URL for resolving relative URLs", "required": True},
        extract_images={"type": "boolean", "default": True, "description": "Whether to extract images"},
        extract_videos={"type": "boolean", "default": False, "description": "Whether to extract videos"},
        min_image_size={"type": "integer", "default": 100, "description": "Minimum image dimension in pixels"}
    )
    def execute(self, soup: BeautifulSoup, base_url: str, extract_images: bool = True, extract_videos: bool = False, min_image_size: int = 100) -> Dict[str, Any]:
        """
        Extract media content from parsed HTML
        
        Args:
            soup: BeautifulSoup parsed HTML
            base_url: Base URL for resolving relative URLs
            extract_images: Whether to extract images
            extract_videos: Whether to extract videos  
            min_image_size: Minimum image dimension threshold
            
        Returns:
            Dict containing extracted media with quality analysis
        """
        self._log_execution()
        
        try:
            # Get domain context for filtering
            domain_context = self._analyze_domain_context(base_url)
            
            extracted_media = {
                "images": [],
                "videos": [],
                "extraction_metadata": {
                    "domain_context": domain_context,
                    "extraction_settings": {
                        "extract_images": extract_images,
                        "extract_videos": extract_videos,
                        "min_image_size": min_image_size
                    }
                }
            }
            
            # Extract images
            if extract_images:
                images_result = self._extract_images(soup, base_url, domain_context, min_image_size)
                extracted_media["images"] = images_result["images"]
                extracted_media["extraction_metadata"]["image_stats"] = images_result["stats"]
            
            # Extract videos
            if extract_videos:
                videos_result = self._extract_videos(soup, base_url, domain_context)
                extracted_media["videos"] = videos_result["videos"]
                extracted_media["extraction_metadata"]["video_stats"] = videos_result["stats"]
            
            return {
                "success": True,
                **extracted_media
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "images": [],
                "videos": []
            }
    
    def _analyze_domain_context(self, url: str) -> Dict[str, Any]:
        """Analyze domain context for intelligent filtering"""
        domain = urlparse(url).netloc.lower()
        
        # Extract company/site name
        domain_parts = domain.split('.')
        if len(domain_parts) >= 2:
            company_name = domain_parts[-2]  # e.g., 'asiaone' from 'www.asiaone.com'
        else:
            company_name = domain
        
        # Classify domain type
        domain_type = self._classify_domain_type(domain)
        
        return {
            "full_domain": domain,
            "company_name": company_name,
            "domain_type": domain_type,
            "is_news_site": domain_type == "news_media",
            "is_blog": domain_type == "blog",
            "is_ecommerce": domain_type == "ecommerce"
        }
    
    def _classify_domain_type(self, domain: str) -> str:
        """Classify the type of domain"""
        if any(keyword in domain for keyword in ['news', 'times', 'post', 'herald', 'guardian', 'asiaone', 'channelnewsasia']):
            return "news_media"
        elif any(keyword in domain for keyword in ['blog', 'medium', 'substack', 'wordpress']):
            return "blog"
        elif any(keyword in domain for keyword in ['shop', 'store', 'buy', 'market', 'ecommerce']):
            return "ecommerce"
        elif any(keyword in domain for keyword in ['edu', 'academic', 'university', 'school']):
            return "educational"
        elif any(keyword in domain for keyword in ['gov', 'official']):
            return "government"
        else:
            return "general"
    
    def _extract_images(self, soup: BeautifulSoup, base_url: str, domain_context: Dict, min_size: int) -> Dict[str, Any]:
        """Extract and analyze images"""
        img_tags = soup.find_all('img')
        images = []
        stats = {
            "total_img_tags": len(img_tags),
            "filtered_out_count": 0,
            "filter_reasons": {}
        }
        
        for i, img in enumerate(img_tags):
            try:
                image_data = self._process_single_image(img, i, base_url, domain_context, min_size)
                
                if image_data:
                    images.append(image_data)
                else:
                    stats["filtered_out_count"] += 1
                    
            except Exception as e:
                stats["filtered_out_count"] += 1
                reason = f"processing_error: {str(e)}"
                stats["filter_reasons"][reason] = stats["filter_reasons"].get(reason, 0) + 1
        
        stats["extracted_count"] = len(images)
        
        return {"images": images, "stats": stats}
    
    def _process_single_image(self, img, index: int, base_url: str, domain_context: Dict, min_size: int) -> Dict[str, Any]:
        """Process a single image element"""
        src = img.get('src')
        if not src:
            return None
        
        # Skip data URIs and tracking pixels
        if self._should_skip_image_url(src):
            return None
        
        # Normalize URL
        normalized_url = self._normalize_media_url(src, base_url)
        alt_text = img.get('alt', '').strip()
        
        # Apply semantic filtering
        if self._should_filter_image(img, alt_text, normalized_url, domain_context):
            return None
        
        # Extract image context and metadata
        context_data = self._extract_image_context(img)
        size_data = self._extract_image_size(img, min_size)
        
        # Calculate preliminary relevance score
        relevance_score = self._calculate_image_relevance_score(
            img, alt_text, normalized_url, context_data, size_data, domain_context
        )
        
        return {
            "id": f"img_{index+1:03d}",
            "src": normalized_url,
            "alt": alt_text,
            "context": context_data,
            "size": size_data,
            "relevance_score": relevance_score,
            "extraction_metadata": {
                "semantic_tags": self._extract_semantic_tags(img, alt_text),
                "quality_indicators": self._get_image_quality_indicators(img, alt_text, size_data),
                "content_type_hint": self._infer_content_type(normalized_url, alt_text)
            }
        }
    
    def _should_skip_image_url(self, src: str) -> bool:
        """Check if image URL should be skipped entirely"""
        src_lower = src.lower()
        
        # Skip data URIs, tracking pixels, and empty sources
        skip_patterns = [
            'data:', 'base64', 'javascript:',
            'pixel.', 'tracking.', 'analytics.',
            'beacon.', '1x1.', 'transparent.'
        ]
        
        return any(pattern in src_lower for pattern in skip_patterns)
    
    def _should_filter_image(self, img, alt_text: str, src: str, domain_context: Dict) -> bool:
        """Apply intelligent semantic filtering"""
        src_lower = src.lower()
        alt_lower = alt_text.lower()
        
        # Filter company logos and branding
        company_name = domain_context.get("company_name", "")
        if company_name and (company_name in src_lower or company_name in alt_lower):
            return True
        
        # Filter generic UI elements
        ui_patterns = [
            'logo', 'icon', 'button', 'arrow', 'bullet',
            'separator', 'divider', 'spacer', 'border'
        ]
        if any(pattern in src_lower or pattern in alt_lower for pattern in ui_patterns):
            return True
        
        # Filter advertising and promotional content
        ad_patterns = [
            'advertisement', 'sponsored', 'promo', 'banner',
            'affiliate', 'partner', 'widget'
        ]
        if any(pattern in src_lower or pattern in alt_lower for pattern in ad_patterns):
            return True
        
        # Filter social media elements
        social_patterns = ['facebook', 'twitter', 'instagram', 'linkedin', 'share', 'follow']
        if any(pattern in src_lower or pattern in alt_lower for pattern in social_patterns):
            return True
        
        # Check structural position
        if self._is_in_non_content_area(img):
            return True
        
        return False
    
    def _is_in_non_content_area(self, img) -> bool:
        """Check if image is in header, footer, sidebar, or navigation"""
        non_content_parents = img.find_parents(['header', 'footer', 'nav', 'aside'])
        if non_content_parents:
            return True
        
        # Check for non-content class names
        parent = img.parent
        while parent:
            parent_classes = parent.get('class', [])
            if isinstance(parent_classes, list):
                class_string = ' '.join(parent_classes).lower()
                non_content_classes = ['header', 'footer', 'sidebar', 'nav', 'menu', 'widget']
                if any(nc_class in class_string for nc_class in non_content_classes):
                    return True
            parent = parent.parent
            if parent.name == 'body':  # Stop at body
                break
        
        return False
    
    def _extract_image_context(self, img) -> Dict[str, Any]:
        """Extract contextual information around the image"""
        context = {
            "surrounding_text": "",
            "caption": "",
            "figure_context": False,
            "article_context": False,
            "parent_element": img.parent.name if img.parent else None
        }
        
        # Check if image is in a figure element
        figure_parent = img.find_parent('figure')
        if figure_parent:
            context["figure_context"] = True
            figcaption = figure_parent.find('figcaption')
            if figcaption:
                context["caption"] = figcaption.get_text(strip=True)
        
        # Check if image is in article context
        article_parent = img.find_parent(['article', 'main', '[role="main"]'])
        if article_parent:
            context["article_context"] = True
        
        # Get surrounding text
        parent = img.parent
        if parent:
            text = parent.get_text(strip=True)
            # Remove the alt text from surrounding text to avoid duplication
            alt_text = img.get('alt', '')
            if alt_text and alt_text in text:
                text = text.replace(alt_text, '').strip()
            context["surrounding_text"] = text[:200]  # Limit length
        
        return context
    
    def _extract_image_size(self, img, min_size: int) -> Dict[str, Any]:
        """Extract and validate image size information"""
        size_data = {
            "width": None,
            "height": None,
            "meets_min_size": False,
            "size_category": "unknown"
        }
        
        try:
            width_attr = img.get('width')
            height_attr = img.get('height')
            
            width = int(width_attr) if width_attr and width_attr.isdigit() else None
            height = int(height_attr) if height_attr and height_attr.isdigit() else None
            
            size_data.update({
                "width": width,
                "height": height
            })
            
            # Determine if image meets minimum size requirements
            if width and height:
                size_data["meets_min_size"] = width >= min_size and height >= min_size
                
                # Categorize by size
                if width >= 800 or height >= 600:
                    size_data["size_category"] = "large"
                elif width >= 400 or height >= 300:
                    size_data["size_category"] = "medium"
                elif width >= min_size or height >= min_size:
                    size_data["size_category"] = "small"
                else:
                    size_data["size_category"] = "tiny"
            
        except (ValueError, TypeError):
            pass
        
        return size_data
    
    def _calculate_image_relevance_score(self, img, alt_text: str, src: str, context: Dict, size: Dict, domain_context: Dict) -> float:
        """Calculate relevance score for image"""
        score = 0.4  # Base score
        
        # Context bonuses
        if context["figure_context"]:
            score += 0.2
        if context["article_context"]:
            score += 0.15
        if context["caption"]:
            score += 0.15
        
        # Alt text quality
        if alt_text and len(alt_text) > 10:
            if not any(generic in alt_text.lower() for generic in ['image', 'photo', 'picture']):
                score += 0.2
        
        # Size bonus
        if size["meets_min_size"]:
            score += 0.1
            if size["size_category"] in ["medium", "large"]:
                score += 0.1
        
        # Content area bonus
        if not self._is_in_non_content_area(img):
            score += 0.1
        
        return min(1.0, max(0.0, score))
    
    def _extract_semantic_tags(self, img, alt_text: str) -> List[str]:
        """Extract semantic tags for the image"""
        tags = []
        
        # Analyze alt text for semantic meaning
        alt_lower = alt_text.lower()
        
        if any(word in alt_lower for word in ['person', 'people', 'man', 'woman', 'child']):
            tags.append('person')
        if any(word in alt_lower for word in ['building', 'house', 'office', 'structure']):
            tags.append('architecture')
        if any(word in alt_lower for word in ['chart', 'graph', 'diagram', 'infographic']):
            tags.append('data_visualization')
        if any(word in alt_lower for word in ['product', 'item', 'device', 'tool']):
            tags.append('product')
        if any(word in alt_lower for word in ['landscape', 'nature', 'outdoors', 'scenery']):
            tags.append('landscape')
        
        # Check parent elements for additional context
        parent = img.parent
        if parent:
            parent_classes = ' '.join(parent.get('class', [])).lower()
            if 'gallery' in parent_classes:
                tags.append('gallery_image')
            if 'hero' in parent_classes or 'banner' in parent_classes:
                tags.append('hero_image')
        
        return tags
    
    def _get_image_quality_indicators(self, img, alt_text: str, size: Dict) -> List[str]:
        """Get quality indicators for the image"""
        indicators = []
        
        if alt_text and len(alt_text) > 20:
            indicators.append('descriptive_alt_text')
        
        if size["meets_min_size"]:
            indicators.append('adequate_size')
        
        if size["size_category"] in ["medium", "large"]:
            indicators.append('substantial_size')
        
        figure_parent = img.find_parent('figure')
        if figure_parent:
            indicators.append('proper_semantic_markup')
        
        if not self._is_in_non_content_area(img):
            indicators.append('content_area_placement')
        
        return indicators
    
    def _infer_content_type(self, src: str, alt_text: str) -> str:
        """Infer the type of content the image represents"""
        src_lower = src.lower()
        alt_lower = alt_text.lower()
        
        # Check file extension and alt text for content type hints
        if any(ext in src_lower for ext in ['.jpg', '.jpeg', '.png', '.webp']):
            if any(word in alt_lower for word in ['screenshot', 'screen', 'interface']):
                return 'screenshot'
            elif any(word in alt_lower for word in ['chart', 'graph', 'data']):
                return 'data_visualization'
            elif any(word in alt_lower for word in ['portrait', 'person', 'people']):
                return 'portrait'
            else:
                return 'photograph'
        
        return 'unknown'
    
    def _extract_videos(self, soup: BeautifulSoup, base_url: str, domain_context: Dict) -> Dict[str, Any]:
        """Extract video content (placeholder for future implementation)"""
        # This is a placeholder for video extraction functionality
        # Could be extended to handle <video>, <iframe> (YouTube/Vimeo), etc.
        
        video_tags = soup.find_all(['video', 'iframe'])
        videos = []
        
        for i, video in enumerate(video_tags):
            if video.name == 'video':
                src = video.get('src')
                if src:
                    videos.append({
                        "id": f"video_{i+1}",
                        "src": self._normalize_media_url(src, base_url),
                        "type": "native_video",
                        "poster": video.get('poster', ''),
                        "controls": video.has_attr('controls')
                    })
            elif video.name == 'iframe':
                src = video.get('src', '')
                if any(platform in src for platform in ['youtube.com', 'vimeo.com', 'dailymotion.com']):
                    videos.append({
                        "id": f"video_{i+1}",
                        "src": src,
                        "type": "embedded_video",
                        "platform": self._detect_video_platform(src)
                    })
        
        return {
            "videos": videos,
            "stats": {
                "total_video_elements": len(video_tags),
                "extracted_videos": len(videos)
            }
        }
    
    def _detect_video_platform(self, src: str) -> str:
        """Detect video platform from URL"""
        src_lower = src.lower()
        if 'youtube.com' in src_lower or 'youtu.be' in src_lower:
            return 'youtube'
        elif 'vimeo.com' in src_lower:
            return 'vimeo'
        elif 'dailymotion.com' in src_lower:
            return 'dailymotion'
        else:
            return 'unknown'
    
    def _normalize_media_url(self, src: str, base_url: str) -> str:
        """Normalize media URL to absolute URL"""
        if src.startswith('//'):
            return 'https:' + src
        elif src.startswith('/'):
            return urljoin(base_url, src)
        elif not src.startswith('http'):
            return urljoin(base_url, src)
        return src
    
    def _log_execution(self):
        """Log tool execution"""
        from datetime import datetime
        self.execution_count += 1
        self.last_execution = datetime.utcnow().isoformat() + "Z"