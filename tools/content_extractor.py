"""
Content Extractor tool using decorator pattern.
"""

import re
import trafilatura
from typing import Dict, Any, List
from bs4 import BeautifulSoup
from urllib.parse import urlparse

from decorators import tool, input_schema


@tool(
    name="ContentExtractor",
    description="Intelligently extracts structured text content from HTML using multiple advanced strategies"
)
class ContentExtractor:
    """Advanced content extraction engine with multiple fallback strategies and quality scoring"""
    
    def __init__(self):
        self.execution_count = 0
        self.last_execution = None
    
    @input_schema(
        soup={"description": "BeautifulSoup parsed HTML object", "required": True},
        url={"type": "string", "description": "Source URL for context", "required": True},
        min_content_length={"type": "integer", "default": 50, "description": "Minimum content length to consider"},
        strategy_preference={"type": "string", "default": "auto", "description": "Extraction strategy: auto, selector, density, trafilatura"}
    )
    def execute(self, soup: BeautifulSoup, url: str, min_content_length: int = 50, strategy_preference: str = "auto") -> Dict[str, Any]:
        """
        Extract structured text content from parsed HTML
        
        Args:
            soup: BeautifulSoup parsed HTML
            url: Source URL for context
            min_content_length: Minimum content length to consider
            strategy_preference: Preferred extraction strategy
            
        Returns:
            Dict containing extracted text blocks with quality metrics
        """
        self._log_execution()
        
        try:
            # Clean up HTML first
            self._clean_html(soup)
            
            # Apply extraction strategy
            extraction_result = self._extract_with_strategy(soup, url, strategy_preference, min_content_length)
            
            if not extraction_result["text_blocks"]:
                # Fallback to aggressive extraction
                extraction_result = self._fallback_extraction(soup, url, min_content_length)
            
            # Post-process extracted content
            processed_blocks = self._post_process_blocks(extraction_result["text_blocks"])
            
            # Calculate quality metrics
            quality_metrics = self._calculate_quality_metrics(processed_blocks)
            
            # Extract additional metadata
            page_title = soup.find('title')
            title = page_title.get_text(strip=True) if page_title else "Untitled"
            
            return {
                "success": True,
                "text_blocks": processed_blocks,
                "title": title,
                "extraction_metadata": {
                    "total_blocks": len(processed_blocks),
                    "total_text_length": quality_metrics["total_length"],
                    "extraction_strategy": extraction_result["strategy_used"],
                    "quality_score": quality_metrics["average_score"],
                    "content_diversity": quality_metrics["diversity_score"],
                    "processing_notes": extraction_result.get("notes", [])
                }
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "text_blocks": []
            }
    
    def _clean_html(self, soup: BeautifulSoup):
        """Remove unwanted HTML elements"""
        # Remove script, style, and navigation elements
        for element in soup(["script", "style", "nav", "header", "footer", "aside"]):
            element.decompose()
        
        # Remove common ad/social elements
        for class_name in ['advertisement', 'ad-container', 'social-share', 'related-posts']:
            for element in soup.find_all(class_=re.compile(class_name, re.I)):
                element.decompose()
    
    def _extract_with_strategy(self, soup: BeautifulSoup, url: str, strategy: str, min_length: int) -> Dict[str, Any]:
        """Extract content using specified strategy"""
        
        if strategy == "selector" or strategy == "auto":
            result = self._extract_with_selectors(soup, min_length)
            if result["text_blocks"]:
                return {"text_blocks": result["text_blocks"], "strategy_used": "css_selectors"}
        
        if strategy == "density" or (strategy == "auto" and not result.get("text_blocks")):
            result = self._extract_with_density(soup, min_length)
            if result["text_blocks"]:
                return {"text_blocks": result["text_blocks"], "strategy_used": "content_density"}
        
        if strategy == "trafilatura" or (strategy == "auto"):
            result = self._extract_with_trafilatura(url, min_length)
            if result["text_blocks"]:
                return {"text_blocks": result["text_blocks"], "strategy_used": "trafilatura"}
        
        return {"text_blocks": [], "strategy_used": "none"}
    
    def _extract_with_selectors(self, soup: BeautifulSoup, min_length: int) -> Dict[str, Any]:
        """Extract using CSS selector strategy"""
        content_selectors = [
            'article', 'main', '[role="main"]',
            '.post-content', '.entry-content', '.content', '.article-content',
            '.story-body', '.post-body', '.article-body', '.text-content',
            '#content', '#main-content', '#article', '#post-content',
            '.entry', '.post', '.story', '.article'
        ]
        
        for selector in content_selectors:
            main_content = soup.select_one(selector)
            if main_content and self._has_substantial_content(main_content, min_length * 4):
                blocks = self._extract_text_blocks(main_content, "css_selector", min_length)
                if blocks:
                    return {"text_blocks": blocks}
        
        return {"text_blocks": []}
    
    def _extract_with_density(self, soup: BeautifulSoup, min_length: int) -> Dict[str, Any]:
        """Extract using content density analysis"""
        candidates = soup.find_all(['div', 'section', 'article', 'main'])
        best_element = None
        best_score = 0
        
        for element in candidates:
            score = self._calculate_density_score(element, min_length)
            if score > best_score:
                best_score = score
                best_element = element
        
        if best_element:
            blocks = self._extract_text_blocks(best_element, "density_analysis", min_length)
            return {"text_blocks": blocks}
        
        return {"text_blocks": []}
    
    def _extract_with_trafilatura(self, url: str, min_length: int) -> Dict[str, Any]:
        """Extract using trafilatura library"""
        try:
            downloaded = trafilatura.fetch_url(url)
            if downloaded:
                content = trafilatura.extract(
                    downloaded, 
                    include_comments=False, 
                    include_tables=True,
                    include_formatting=False
                )
                if content and len(content) > min_length * 2:
                    return {
                        "text_blocks": [{
                            "id": "trafilatura_1",
                            "text": content,
                            "token_count": len(content.split()),
                            "element": "trafilatura",
                            "extraction_method": "trafilatura"
                        }]
                    }
        except Exception:
            pass
        
        return {"text_blocks": []}
    
    def _fallback_extraction(self, soup: BeautifulSoup, url: str, min_length: int) -> Dict[str, Any]:
        """Fallback extraction from body element"""
        body = soup.find('body')
        if body:
            blocks = self._extract_text_blocks(body, "body_fallback", min_length)
            return {"text_blocks": blocks, "strategy_used": "body_fallback"}
        
        return {"text_blocks": [], "strategy_used": "failed"}
    
    def _extract_text_blocks(self, element, method: str, min_length: int) -> List[Dict]:
        """Extract text blocks from HTML element"""
        text_elements = element.find_all(['p', 'div', 'section', 'article', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6'])
        blocks = []
        
        for i, elem in enumerate(text_elements):
            text = elem.get_text(strip=True)
            
            if len(text) >= min_length and self._is_content_relevant(text, elem):
                blocks.append({
                    "id": f"{method}_{i+1}",
                    "text": text,
                    "token_count": len(text.split()),
                    "element": elem.name,
                    "extraction_method": method,
                    "character_count": len(text)
                })
        
        return self._deduplicate_blocks(blocks)
    
    def _calculate_density_score(self, element, min_length: int) -> float:
        """Calculate content density score"""
        text_length = len(element.get_text(strip=True))
        if text_length < min_length:
            return 0
            
        tag_count = len(element.find_all())
        link_count = len(element.find_all('a'))
        
        # Penalize high link density and excessive tags
        denominator = max(tag_count + (link_count * 3), 1)
        density_score = text_length / denominator
        
        # Boost score for substantial content
        if text_length > min_length * 10:
            density_score *= 1.5
        
        return density_score
    
    def _has_substantial_content(self, element, min_length: int) -> bool:
        """Check if element has substantial content"""
        if not element:
            return False
        text = element.get_text(strip=True)
        return len(text) >= min_length
    
    def _is_content_relevant(self, text: str, element) -> bool:
        """Enhanced relevance filtering"""
        # Skip obvious non-content - but be less aggressive
        if self._is_navigation_content(text):
            return False
        
        # Remove promotional filtering to get more content
        # if self._is_promotional_content(text):
        #     return False
        
        # Relax excessive links check
        if self._has_excessive_links(text, element, threshold=0.8):
            return False
        
        # Check for meaningful content patterns - relaxed
        return self._has_meaningful_content(text, min_words=5)
    
    def _is_navigation_content(self, text: str) -> bool:
        """Check for navigation patterns"""
        text_lower = text.lower().strip()
        nav_patterns = [
            r'^home\s*>',  # Breadcrumbs
            r'^\d{1,2}:\d{2}\s*(am|pm)$',  # Timestamps only
            r'^(share|like|comment|follow)$',  # Social buttons
            r'^\d+\s*(views?|likes?|shares?)$',  # Metrics only
            r'^(next|previous|back|continue)$'  # Navigation
        ]
        
        return any(re.search(pattern, text_lower) for pattern in nav_patterns)
    
    def _is_promotional_content(self, text: str) -> bool:
        """Check for promotional/advertising content"""
        promo_keywords = [
            'advertisement', 'sponsored', 'promoted', 'affiliate',
            'subscribe now', 'sign up', 'register free', 'download app',
            'special offer', 'limited time', 'act now', 'call now'
        ]
        
        text_lower = text.lower()
        return any(keyword in text_lower for keyword in promo_keywords)
    
    def _has_excessive_links(self, text: str, element, threshold: float = 0.5) -> bool:
        """Check for excessive link density"""
        if not element:
            return False
            
        links = element.find_all('a')
        if not links:
            return False
        
        link_text_length = sum(len(link.get_text(strip=True)) for link in links)
        total_text_length = len(text)
        
        return total_text_length > 0 and (link_text_length / total_text_length) > threshold
    
    def _has_meaningful_content(self, text: str, min_words: int = 10) -> bool:
        """Check if text contains meaningful content"""
        # Relaxed meaningful content check
        word_count = len(text.split())
        
        # Much more relaxed requirements
        return word_count >= min_words
    
    def _deduplicate_blocks(self, blocks: List[Dict]) -> List[Dict]:
        """Remove duplicate content blocks"""
        if not blocks:
            return blocks
        
        unique_blocks = []
        seen_texts = set()
        
        for block in blocks:
            text = block['text']
            normalized = re.sub(r'\s+', ' ', text.lower().strip())
            
            # Check for substantial overlap with existing content
            is_duplicate = False
            for seen_text in seen_texts:
                similarity = self._calculate_text_similarity(normalized, seen_text)
                if similarity > 0.95:  # 95% similarity threshold - less aggressive deduplication
                    is_duplicate = True
                    break
            
            if not is_duplicate:
                unique_blocks.append(block)
                seen_texts.add(normalized)
        
        return unique_blocks
    
    def _calculate_text_similarity(self, text1: str, text2: str) -> float:
        """Calculate similarity between two texts"""
        words1 = set(text1.split())
        words2 = set(text2.split())
        
        if not words1 or not words2:
            return 0.0
        
        intersection = len(words1 & words2)
        union = len(words1 | words2)
        
        return intersection / union if union > 0 else 0.0
    
    def _post_process_blocks(self, blocks: List[Dict]) -> List[Dict]:
        """Post-process extracted blocks with quality scoring"""
        for block in blocks:
            # Calculate quality score
            score = self._calculate_content_quality_score(block["text"])
            
            # Add metadata
            block.update({
                "score": score,
                "quality_indicators": self._get_quality_indicators(block["text"], score),
                "section_path": ["article", "main"],
                "heading_ids": [],
                "links": []
            })
        
        # Sort by quality score
        return sorted(blocks, key=lambda x: x["score"], reverse=True)
    
    def _calculate_content_quality_score(self, text: str) -> float:
        """Calculate comprehensive content quality score"""
        score = 0.5  # Base score
        
        # Length factor (optimal range: 100-1000 chars)
        length = len(text)
        if 100 <= length <= 1000:
            score += 0.2
        elif length > 1000:
            score += 0.15
        elif length >= 50:
            score += 0.1
        
        # Sentence structure
        sentences = [s.strip() for s in text.split('.') if len(s.strip()) > 10]
        if len(sentences) >= 3:
            score += 0.15
        elif len(sentences) >= 2:
            score += 0.1
        
        # Word diversity
        words = text.lower().split()
        if len(words) > 0:
            unique_ratio = len(set(words)) / len(words)
            if unique_ratio > 0.7:
                score += 0.15
            elif unique_ratio > 0.5:
                score += 0.1
        
        # Proper punctuation and formatting
        if any(char in text for char in '.!?'):
            score += 0.05
        if any(char in text for char in ',:;'):
            score += 0.05
        
        # Penalize poor quality indicators
        if text.isupper():
            score -= 0.2
        if len(re.findall(r'\b\w+\b', text)) < 10:
            score -= 0.1
        
        return max(0.0, min(1.0, score))
    
    def _get_quality_indicators(self, text: str, score: float) -> List[str]:
        """Generate quality indicators for content"""
        indicators = []
        
        if len(text) > 500:
            indicators.append("substantial_length")
        if len(text.split('.')) > 3:
            indicators.append("multiple_sentences")
        
        words = text.lower().split()
        if len(words) > 0:
            unique_ratio = len(set(words)) / len(words)
            if unique_ratio > 0.7:
                indicators.append("diverse_vocabulary")
        
        if score > 0.8:
            indicators.append("high_quality")
        elif score > 0.6:
            indicators.append("good_quality")
        
        return indicators
    
    def _calculate_quality_metrics(self, blocks: List[Dict]) -> Dict[str, Any]:
        """Calculate overall quality metrics for extracted content"""
        if not blocks:
            return {"total_length": 0, "average_score": 0.0, "diversity_score": 0.0}
        
        total_length = sum(len(block["text"]) for block in blocks)
        scores = [block.get("score", 0.5) for block in blocks]
        average_score = sum(scores) / len(scores)
        
        # Calculate content diversity
        all_words = set()
        for block in blocks:
            all_words.update(block["text"].lower().split())
        
        total_words = sum(len(block["text"].split()) for block in blocks)
        diversity_score = len(all_words) / total_words if total_words > 0 else 0.0
        
        return {
            "total_length": total_length,
            "average_score": average_score,
            "diversity_score": diversity_score
        }
    
    def _log_execution(self):
        """Log tool execution"""
        from datetime import datetime
        self.execution_count += 1
        self.last_execution = datetime.utcnow().isoformat() + "Z"