"""
Content Filter tool for applying heuristic filtering to extracted content.
"""

from typing import Dict, Any, List

from .base_tool import BaseTool


class ContentFilter(BaseTool):
    """Tool for applying heuristic filtering to text and image content"""
    
    def __init__(self):
        super().__init__(
            name="ContentFilter",
            description="Applies heuristic filtering to remove low-quality or irrelevant content"
        )
    
    def execute(self, content_type: str, content_data: List[Dict], **kwargs) -> Dict[str, Any]:
        """
        Apply content filtering
        
        Args:
            content_type: Type of content ('text' or 'images')
            content_data: List of content items to filter
            **kwargs: Additional filtering parameters
            
        Returns:
            Dict containing filtered content and filter statistics
        """
        self._log_execution()
        
        try:
            if content_type == 'text':
                return self._filter_text_content(content_data, **kwargs)
            elif content_type == 'images':
                return self._filter_image_content(content_data, **kwargs)
            else:
                return {
                    "success": False,
                    "error": f"Unsupported content type: {content_type}"
                }
                
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "filtered_content": content_data  # Return original on error
            }
    
    def _filter_text_content(self, text_blocks: List[Dict], min_score: float = 0.6) -> Dict[str, Any]:
        """Filter text content based on quality scores"""
        filtered_blocks = []
        rejected_blocks = []
        
        for block in text_blocks:
            score = block.get('score', 0.5)
            
            if score >= min_score:
                filtered_blocks.append(block)
            else:
                rejection_reason = f"Score too low: {score:.2f} < {min_score}"
                rejected_blocks.append({
                    "block_id": block.get('id', 'unknown'),
                    "reason": rejection_reason,
                    "score": score,
                    "text_preview": block.get('text', '')[:100] + "..."
                })
        
        return {
            "success": True,
            "content_type": "text",
            "filtered_content": filtered_blocks,
            "filter_stats": {
                "original_count": len(text_blocks),
                "filtered_count": len(filtered_blocks),
                "rejected_count": len(rejected_blocks),
                "rejection_rate": len(rejected_blocks) / len(text_blocks) if text_blocks else 0,
                "rejected_items": rejected_blocks
            }
        }
    
    def _filter_image_content(self, images: List[Dict], min_score: float = 0.2) -> Dict[str, Any]:
        """Filter image content based on heuristic scores"""
        filtered_images = []
        rejected_images = []
        
        for img in images:
            # Calculate basic heuristic score
            score = self._calculate_image_score(img)
            img['basic_score'] = score
            
            if score >= min_score:
                filtered_images.append(img)
            else:
                rejection_reason = self._get_image_rejection_reason(img, score)
                rejected_images.append({
                    "image_id": img.get('id', 'unknown'),
                    "src": img.get('src', '')[:80] + "..." if len(img.get('src', '')) > 80 else img.get('src', ''),
                    "reason": rejection_reason,
                    "score": score
                })
        
        return {
            "success": True,
            "content_type": "images",
            "filtered_content": filtered_images,
            "filter_stats": {
                "original_count": len(images),
                "filtered_count": len(filtered_images),
                "rejected_count": len(rejected_images),
                "rejection_rate": len(rejected_images) / len(images) if images else 0,
                "rejected_items": rejected_images
            }
        }
    
    def _calculate_image_score(self, img: Dict) -> float:
        """Calculate heuristic score for an image"""
        score = 0.4  # Reasonable baseline
        
        src = img.get("src", "").lower()
        alt = img.get("alt", "").lower()
        
        # Check for generic/stock image patterns in URL
        generic_patterns = [
            'icon', 'logo', 'button', 'arrow', 'social', 'header', 'footer',
            'banner', 'ad', 'advertisement', 'stock', 'generic', 'placeholder',
            'shutterstock', 'getty', 'unsplash', 'pexels', 'pixabay',
            'avatar', 'profile', 'user', 'default', 'thumbnail',
            'sponsored', 'promo', 'widget', 'sidebar'
        ]
        
        if any(pattern in src for pattern in generic_patterns):
            score -= 0.3
        
        # Check for generic alt text patterns
        generic_alt_patterns = [
            'image', 'photo', 'picture', 'graphic', 'illustration',
            'stock photo', 'getty images', 'shutterstock', 'file photo',
            'logo', 'icon', 'button', 'advertisement', 'ad',
            'related', 'more', 'click', 'link', 'here'
        ]
        
        if any(pattern in alt for pattern in generic_alt_patterns):
            score -= 0.15
        elif len(alt) > 20 and not any(pattern in alt for pattern in generic_alt_patterns):
            score += 0.3
        
        # Check image size
        try:
            width = int(img.get("width", 0)) if img.get("width") else 0
            height = int(img.get("height", 0)) if img.get("height") else 0
            if width > 400 and height > 300:
                score += 0.3
            elif width > 200 and height > 150:
                score += 0.2
            elif width < 100 or height < 100:
                score -= 0.3
        except ValueError:
            pass
        
        # Check navigation placement
        if img.get("is_navigation", False):
            score -= 0.2
        
        # Check context
        context = img.get("context_text", "").lower()
        if context:
            header_footer_keywords = ['header', 'footer', 'nav', 'menu', 'sidebar', 'related articles', 'advertisement']
            if any(keyword in context for keyword in header_footer_keywords):
                score -= 0.3
        
        # Check company domain
        company_domain = img.get("company_domain", "")
        if company_domain and company_domain in src:
            score -= 0.3
        
        return max(0.0, min(score, 1.0))
    
    def _get_image_rejection_reason(self, img: Dict, score: float) -> str:
        """Generate detailed rejection reason for an image"""
        if score >= 0.2:
            return "Passed basic filtering"
        
        reasons = []
        src = img.get("src", "").lower()
        alt = img.get("alt", "").lower()
        
        # Check URL patterns
        generic_patterns = [
            'icon', 'logo', 'button', 'arrow', 'social', 'header', 'footer',
            'banner', 'ad', 'advertisement', 'stock', 'generic', 'placeholder',
            'shutterstock', 'getty', 'unsplash', 'pexels', 'pixabay',
            'avatar', 'profile', 'user', 'default', 'thumbnail',
            'sponsored', 'promo', 'widget', 'sidebar'
        ]
        
        if any(pattern in src for pattern in generic_patterns):
            matching_patterns = [p for p in generic_patterns if p in src]
            reasons.append(f"URL contains: {', '.join(matching_patterns)}")
        
        # Check alt text
        generic_alt_patterns = [
            'image', 'photo', 'picture', 'graphic', 'illustration',
            'stock photo', 'getty images', 'shutterstock', 'file photo',
            'logo', 'icon', 'button', 'advertisement', 'ad',
            'related', 'more', 'click', 'link', 'here'
        ]
        
        if any(pattern in alt for pattern in generic_alt_patterns):
            matching_alt = [p for p in generic_alt_patterns if p in alt]
            reasons.append(f"Alt text contains: {', '.join(matching_alt)}")
        elif not alt:
            reasons.append("No alt text")
        
        # Check size
        try:
            width = int(img.get("width", 0)) if img.get("width") else 0
            height = int(img.get("height", 0)) if img.get("height") else 0
            if width < 100 or height < 100:
                reasons.append(f"Too small ({width}x{height})")
        except ValueError:
            pass
        
        # Check navigation
        if img.get("is_navigation", False):
            reasons.append("In navigation area")
        
        # Check company domain
        company_domain = img.get("company_domain", "")
        if company_domain and company_domain in src:
            reasons.append("Company domain image")
        
        # Check context
        context = img.get("context_text", "").lower()
        if context:
            header_footer_keywords = ['header', 'footer', 'nav', 'menu', 'sidebar', 'related articles', 'advertisement']
            if any(keyword in context for keyword in header_footer_keywords):
                matching_context = [k for k in header_footer_keywords if k in context]
                reasons.append(f"Context: {', '.join(matching_context)}")
        
        if not reasons:
            reasons.append(f"Low score ({score:.2f})")
        
        return " | ".join(reasons)
    
    def _get_input_schema(self) -> Dict[str, Any]:
        """Define input schema for Strands SDK"""
        return {
            "type": "object",
            "properties": {
                "content_type": {
                    "type": "string",
                    "enum": ["text", "images"],
                    "description": "Type of content to filter"
                },
                "content_data": {
                    "type": "array",
                    "description": "List of content items to filter"
                },
                "min_score": {
                    "type": "number",
                    "description": "Minimum score threshold for filtering",
                    "default": 0.6
                }
            },
            "required": ["content_type", "content_data"]
        }