"""
Quality Filter tool using decorator pattern.
"""

from typing import Dict, Any, List
from decorators import tool, input_schema


@tool(
    name="QualityFilter",
    description="Applies intelligent quality filtering to content using advanced heuristics and scoring"
)
class QualityFilter:
    """Advanced quality filtering engine for text and media content"""
    
    def __init__(self):
        self.execution_count = 0
        self.last_execution = None
        self.filter_stats = {"total_filtered": 0, "sessions": []}
    
    @input_schema(
        content_type={"type": "string", "enum": ["text", "images", "videos"], "required": True, "description": "Type of content to filter"},
        content_data={"type": "array", "required": True, "description": "List of content items to filter"},
        quality_threshold={"type": "number", "default": 0.6, "description": "Minimum quality score (0.0-1.0)"},
        strictness_level={"type": "string", "enum": ["lenient", "balanced", "strict"], "default": "balanced", "description": "Filtering strictness level"},
        preserve_high_value={"type": "boolean", "default": True, "description": "Always preserve highest-value content even if below threshold"}
    )
    def execute(self, content_type: str, content_data: List[Dict], quality_threshold: float = 0.6, 
                strictness_level: str = "balanced", preserve_high_value: bool = True) -> Dict[str, Any]:
        """
        Apply intelligent quality filtering to content
        
        Args:
            content_type: Type of content ('text', 'images', 'videos')
            content_data: List of content items to filter
            quality_threshold: Minimum quality score (0.0-1.0)
            strictness_level: Filtering strictness ('lenient', 'balanced', 'strict')
            preserve_high_value: Always preserve highest-value content
            
        Returns:
            Dict containing filtered content with detailed statistics
        """
        self._log_execution()
        
        try:
            if not content_data:
                return self._create_empty_result(content_type)
            
            # Adjust threshold based on strictness level
            adjusted_threshold = self._adjust_threshold(quality_threshold, strictness_level)
            
            # Apply content-specific filtering
            if content_type == "text":
                return self._filter_text_content(content_data, adjusted_threshold, preserve_high_value, strictness_level)
            elif content_type == "images":
                return self._filter_image_content(content_data, adjusted_threshold, preserve_high_value, strictness_level)
            elif content_type == "videos":
                return self._filter_video_content(content_data, adjusted_threshold, preserve_high_value, strictness_level)
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
    
    def _adjust_threshold(self, base_threshold: float, strictness: str) -> float:
        """Adjust threshold based on strictness level"""
        adjustments = {
            "lenient": -0.1,
            "balanced": 0.0,
            "strict": +0.15
        }
        return max(0.1, min(0.95, base_threshold + adjustments.get(strictness, 0.0)))
    
    def _filter_text_content(self, text_blocks: List[Dict], threshold: float, preserve_high_value: bool, strictness: str) -> Dict[str, Any]:
        """Filter text content with advanced quality analysis"""
        if not text_blocks:
            return self._create_empty_result("text")
        
        # Recalculate scores for all blocks
        scored_blocks = [self._enhance_text_scoring(block) for block in text_blocks]
        
        # Sort by quality score
        scored_blocks.sort(key=lambda x: x.get('enhanced_score', x.get('score', 0)), reverse=True)
        
        filtered_blocks = []
        rejected_blocks = []
        
        # Always preserve top content if preserve_high_value is True
        if preserve_high_value and scored_blocks:
            top_block = scored_blocks[0]
            if top_block.get('enhanced_score', top_block.get('score', 0)) >= 0.4:  # Very low bar for top content
                filtered_blocks.append(top_block)
                scored_blocks = scored_blocks[1:]
        
        # Apply threshold filtering to remaining blocks
        for block in scored_blocks:
            score = block.get('enhanced_score', block.get('score', 0))
            
            if score >= threshold:
                filtered_blocks.append(block)
            else:
                rejected_blocks.append({
                    "block_id": block.get('id', 'unknown'),
                    "reason": self._generate_text_rejection_reason(block, score, threshold),
                    "score": score,
                    "text_preview": block.get('text', '')[:100] + "..." if len(block.get('text', '')) > 100 else block.get('text', '')
                })
        
        # Apply strictness-based additional filtering
        if strictness == "strict" and len(filtered_blocks) > 3:
            # Keep only top 3 blocks in strict mode
            rejected_additional = filtered_blocks[3:]
            filtered_blocks = filtered_blocks[:3]
            
            for block in rejected_additional:
                rejected_blocks.append({
                    "block_id": block.get('id', 'unknown'),
                    "reason": "Strict mode: Exceeded maximum block limit (3)",
                    "score": block.get('enhanced_score', block.get('score', 0))
                })
        
        return {
            "success": True,
            "content_type": "text",
            "filtered_content": filtered_blocks,
            "filter_stats": self._generate_filter_stats("text", text_blocks, filtered_blocks, rejected_blocks, threshold, strictness)
        }
    
    def _enhance_text_scoring(self, block: Dict) -> Dict:
        """Enhance text scoring with additional quality metrics"""
        text = block.get('text', '')
        existing_score = block.get('score', 0.5)
        
        # Advanced quality indicators
        enhanced_score = existing_score
        quality_bonuses = []
        quality_penalties = []
        
        # Length optimization (sweet spot analysis)
        length = len(text)
        if 150 <= length <= 800:  # Optimal range
            enhanced_score += 0.1
            quality_bonuses.append("optimal_length")
        elif length > 1500:  # Too long, might be low quality
            enhanced_score -= 0.05
            quality_penalties.append("excessive_length")
        
        # Readability analysis
        sentences = [s.strip() for s in text.split('.') if len(s.strip()) > 5]
        if sentences:
            avg_sentence_length = sum(len(s.split()) for s in sentences) / len(sentences)
            if 8 <= avg_sentence_length <= 25:  # Good readability range
                enhanced_score += 0.08
                quality_bonuses.append("good_readability")
        
        # Content richness
        words = text.lower().split()
        if len(words) > 10:
            unique_words = len(set(words))
            diversity_ratio = unique_words / len(words)
            
            if diversity_ratio > 0.8:
                enhanced_score += 0.12
                quality_bonuses.append("high_lexical_diversity")
            elif diversity_ratio < 0.4:
                enhanced_score -= 0.08
                quality_penalties.append("low_lexical_diversity")
        
        # Information density
        info_indicators = len([word for word in words if len(word) > 6])  # Complex words
        info_density = info_indicators / len(words) if words else 0
        if info_density > 0.15:
            enhanced_score += 0.1
            quality_bonuses.append("information_dense")
        
        # Structural quality
        has_proper_punctuation = any(p in text for p in '.!?;:,')
        has_varied_punctuation = len(set(c for c in text if c in '.!?;:,')) >= 2
        
        if has_proper_punctuation and has_varied_punctuation:
            enhanced_score += 0.05
            quality_bonuses.append("proper_structure")
        
        # Update block with enhanced information
        enhanced_block = block.copy()
        enhanced_block.update({
            'enhanced_score': max(0.0, min(1.0, enhanced_score)),
            'quality_bonuses': quality_bonuses,
            'quality_penalties': quality_penalties,
            'quality_analysis': {
                'length_category': self._categorize_text_length(length),
                'readability_score': avg_sentence_length if 'sentences' in locals() else 0,
                'diversity_ratio': diversity_ratio if 'diversity_ratio' in locals() else 0,
                'info_density': info_density
            }
        })
        
        return enhanced_block
    
    def _categorize_text_length(self, length: int) -> str:
        """Categorize text length"""
        if length < 50:
            return "very_short"
        elif length < 150:
            return "short"
        elif length < 400:
            return "medium"
        elif length < 800:
            return "long"
        else:
            return "very_long"
    
    def _filter_image_content(self, images: List[Dict], threshold: float, preserve_high_value: bool, strictness: str) -> Dict[str, Any]:
        """Filter image content with enhanced scoring"""
        if not images:
            return self._create_empty_result("images")
        
        # Enhance scoring for all images
        scored_images = [self._enhance_image_scoring(img) for img in images]
        
        # Sort by enhanced score
        scored_images.sort(key=lambda x: x.get('enhanced_relevance_score', x.get('relevance_score', 0)), reverse=True)
        
        filtered_images = []
        rejected_images = []
        
        # Preserve high-value content
        if preserve_high_value and scored_images:
            top_image = scored_images[0]
            top_score = top_image.get('enhanced_relevance_score', top_image.get('relevance_score', 0))
            if top_score >= 0.3:  # Lower bar for top image
                filtered_images.append(top_image)
                scored_images = scored_images[1:]
        
        # Apply threshold filtering
        for img in scored_images:
            score = img.get('enhanced_relevance_score', img.get('relevance_score', 0))
            
            if score >= threshold:
                filtered_images.append(img)
            else:
                rejected_images.append({
                    "image_id": img.get('id', 'unknown'),
                    "src": img.get('src', '')[:80] + "..." if len(img.get('src', '')) > 80 else img.get('src', ''),
                    "reason": self._generate_image_rejection_reason(img, score, threshold),
                    "score": score
                })
        
        # Strictness-based additional filtering
        if strictness == "strict" and len(filtered_images) > 2:
            # Keep only top 2 images in strict mode
            rejected_additional = filtered_images[2:]
            filtered_images = filtered_images[:2]
            
            for img in rejected_additional:
                rejected_images.append({
                    "image_id": img.get('id', 'unknown'),
                    "src": img.get('src', '')[:80] + "...",
                    "reason": "Strict mode: Exceeded maximum image limit (2)",
                    "score": img.get('enhanced_relevance_score', img.get('relevance_score', 0))
                })
        
        return {
            "success": True,
            "content_type": "images",
            "filtered_content": filtered_images,
            "filter_stats": self._generate_filter_stats("images", images, filtered_images, rejected_images, threshold, strictness)
        }
    
    def _enhance_image_scoring(self, img: Dict) -> Dict:
        """Enhance image scoring with additional quality metrics"""
        base_score = img.get('relevance_score', 0.4)
        enhanced_score = base_score
        
        # Context quality bonuses
        context = img.get('context', {})
        if context.get('figure_context'):
            enhanced_score += 0.15
        if context.get('caption'):
            enhanced_score += 0.1
        if context.get('article_context'):
            enhanced_score += 0.1
        
        # Alt text quality
        alt_text = img.get('alt', '')
        if alt_text and len(alt_text) > 15:
            if not any(generic in alt_text.lower() for generic in ['image', 'photo', 'picture', 'img']):
                enhanced_score += 0.15
        
        # Size and quality indicators
        quality_indicators = img.get('extraction_metadata', {}).get('quality_indicators', [])
        enhanced_score += len(quality_indicators) * 0.05
        
        # Semantic tags bonus
        semantic_tags = img.get('extraction_metadata', {}).get('semantic_tags', [])
        if semantic_tags:
            enhanced_score += min(0.1, len(semantic_tags) * 0.03)
        
        # Update image with enhanced scoring
        enhanced_img = img.copy()
        enhanced_img['enhanced_relevance_score'] = max(0.0, min(1.0, enhanced_score))
        
        return enhanced_img
    
    def _filter_video_content(self, videos: List[Dict], threshold: float, preserve_high_value: bool, strictness: str) -> Dict[str, Any]:
        """Filter video content (placeholder for future enhancement)"""
        # Basic video filtering - can be enhanced later
        filtered_videos = [video for video in videos if video.get('relevance_score', 0.5) >= threshold]
        rejected_videos = []
        
        for video in videos:
            if video not in filtered_videos:
                rejected_videos.append({
                    "video_id": video.get('id', 'unknown'),
                    "src": video.get('src', ''),
                    "reason": f"Score {video.get('relevance_score', 0.5):.2f} below threshold {threshold:.2f}",
                    "score": video.get('relevance_score', 0.5)
                })
        
        return {
            "success": True,
            "content_type": "videos",
            "filtered_content": filtered_videos,
            "filter_stats": self._generate_filter_stats("videos", videos, filtered_videos, rejected_videos, threshold, strictness)
        }
    
    def _generate_text_rejection_reason(self, block: Dict, score: float, threshold: float) -> str:
        """Generate detailed rejection reason for text block"""
        reasons = [f"Score {score:.2f} below threshold {threshold:.2f}"]
        
        # Add specific quality issues
        penalties = block.get('quality_penalties', [])
        if penalties:
            reasons.append(f"Quality issues: {', '.join(penalties)}")
        
        analysis = block.get('quality_analysis', {})
        if analysis.get('length_category') == 'very_short':
            reasons.append("Content too short")
        elif analysis.get('diversity_ratio', 1.0) < 0.4:
            reasons.append("Low content diversity")
        
        return " | ".join(reasons)
    
    def _generate_image_rejection_reason(self, img: Dict, score: float, threshold: float) -> str:
        """Generate detailed rejection reason for image"""
        reasons = [f"Score {score:.2f} below threshold {threshold:.2f}"]
        
        # Check for specific issues
        if not img.get('alt'):
            reasons.append("Missing alt text")
        
        context = img.get('context', {})
        if not context.get('article_context'):
            reasons.append("Not in article context")
        
        quality_indicators = img.get('extraction_metadata', {}).get('quality_indicators', [])
        if not quality_indicators:
            reasons.append("No quality indicators")
        
        return " | ".join(reasons)
    
    def _generate_filter_stats(self, content_type: str, original: List, filtered: List, rejected: List, threshold: float, strictness: str) -> Dict[str, Any]:
        """Generate comprehensive filtering statistics"""
        original_count = len(original)
        filtered_count = len(filtered)
        rejected_count = len(rejected)
        
        stats = {
            "original_count": original_count,
            "filtered_count": filtered_count,
            "rejected_count": rejected_count,
            "retention_rate": filtered_count / original_count if original_count > 0 else 0,
            "quality_threshold": threshold,
            "strictness_level": strictness,
            "rejected_items": rejected[:5],  # Sample of rejected items
            "filter_effectiveness": {
                "avg_score_filtered": sum(item.get('enhanced_score', item.get('score', item.get('relevance_score', 0))) for item in filtered) / filtered_count if filtered_count > 0 else 0,
                "score_improvement": 0  # Could calculate if we tracked before/after scores
            }
        }
        
        # Add content-specific stats
        if content_type == "text":
            stats["text_stats"] = {
                "total_characters": sum(len(item.get('text', '')) for item in filtered),
                "avg_block_length": sum(len(item.get('text', '')) for item in filtered) / filtered_count if filtered_count > 0 else 0
            }
        elif content_type == "images":
            stats["image_stats"] = {
                "with_alt_text": sum(1 for item in filtered if item.get('alt')),
                "in_article_context": sum(1 for item in filtered if item.get('context', {}).get('article_context')),
                "with_captions": sum(1 for item in filtered if item.get('context', {}).get('caption'))
            }
        
        return stats
    
    def _create_empty_result(self, content_type: str) -> Dict[str, Any]:
        """Create result for empty content"""
        return {
            "success": True,
            "content_type": content_type,
            "filtered_content": [],
            "filter_stats": {
                "original_count": 0,
                "filtered_count": 0,
                "rejected_count": 0,
                "retention_rate": 0,
                "rejected_items": []
            }
        }
    
    def _log_execution(self):
        """Log tool execution"""
        from datetime import datetime
        self.execution_count += 1
        self.last_execution = datetime.utcnow().isoformat() + "Z"
        self.filter_stats["total_filtered"] += 1