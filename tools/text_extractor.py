"""
Text Extractor tool for extracting and processing text content from HTML.
"""

import re
import trafilatura
from typing import Dict, Any, List
from bs4 import BeautifulSoup
from urllib.parse import urlparse

from .base_tool import BaseTool


class TextExtractor(BaseTool):
    """Tool for extracting structured text content from HTML"""
    
    def __init__(self):
        super().__init__(
            name="TextExtractor",
            description="Extracts and structures text content from HTML using multiple strategies"
        )
    
    def execute(self, soup: BeautifulSoup, url: str) -> Dict[str, Any]:
        """
        Extract text content from parsed HTML
        
        Args:
            soup: BeautifulSoup parsed HTML
            url: Source URL for context
            
        Returns:
            Dict containing extracted text blocks and metadata
        """
        self._log_execution()
        
        try:
            # Remove script and style elements
            for script in soup(["script", "style", "nav", "header", "footer"]):
                script.decompose()
            
            # Strategy 1: Enhanced selector priority chain
            content_selectors = [
                'article', 'main', '[role="main"]',
                '.post-content', '.entry-content', '.content', '.article-content',
                '.story-body', '.post-body', '.article-body', '.text-content',
                '#content', '#main-content', '#article', '#post-content',
                '.entry', '.post', '.story', '.article'
            ]
            
            main_content = None
            for selector in content_selectors:
                main_content = soup.select_one(selector)
                if main_content and self._has_substantial_content(main_content):
                    break
            
            # Strategy 2: Content density heuristics if selectors fail
            if not main_content or not self._has_substantial_content(main_content):
                main_content = self._find_content_by_density(soup)
            
            # Strategy 3: Trafilatura fallback
            text_blocks = []
            if not main_content or not self._has_substantial_content(main_content):
                trafilatura_content = self._extract_with_trafilatura(url)
                if trafilatura_content:
                    text_blocks = [{
                        "id": "t1",
                        "text": trafilatura_content,
                        "token_count": len(trafilatura_content.split()),
                        "element": "trafilatura",
                        "extraction_method": "trafilatura_fallback"
                    }]
            
            # Strategy 4: Extract from main content
            if not text_blocks and main_content:
                text_blocks = self._extract_text_blocks(main_content)
            
            # Strategy 5: Body fallback
            if not text_blocks:
                body = soup.find('body')
                if body:
                    text_blocks = self._extract_text_blocks(body)
            
            # Remove duplicates and apply quality scoring
            text_blocks = self._deduplicate_blocks(text_blocks)
            text_blocks = self._score_text_blocks(text_blocks)
            
            # Extract additional metadata
            title = soup.find('title')
            title_text = title.get_text(strip=True) if title else "Untitled"
            
            return {
                "success": True,
                "text_blocks": text_blocks,
                "title": title_text,
                "extraction_metadata": {
                    "total_blocks": len(text_blocks),
                    "total_text_length": sum(len(block["text"]) for block in text_blocks),
                    "extraction_strategy": self._get_extraction_strategy(text_blocks),
                    "quality_score": self._calculate_overall_quality(text_blocks)
                }
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "text_blocks": []
            }
    
    def _extract_text_blocks(self, element) -> List[Dict]:
        """Extract text blocks from HTML element"""
        text_elements = element.find_all(['p', 'div', 'section', 'article', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6'])
        blocks = []
        
        for i, elem in enumerate(text_elements):
            text = elem.get_text(strip=True)
            
            if len(text) > 50 and self._is_relevant_content(text, elem):
                blocks.append({
                    "id": f"t{i+1}",
                    "text": text,
                    "token_count": len(text.split()),
                    "element": elem.name,
                    "extraction_method": "selector_based"
                })
        
        return blocks
    
    def _has_substantial_content(self, element) -> bool:
        """Check if element has substantial text content"""
        if not element:
            return False
        text = element.get_text(strip=True)
        return len(text) > 200
    
    def _find_content_by_density(self, soup: BeautifulSoup):
        """Find content using density heuristics"""
        candidates = soup.find_all(['div', 'section', 'article'])
        best_element = None
        best_score = 0
        
        for element in candidates:
            text_length = len(element.get_text(strip=True))
            if text_length < 100:
                continue
                
            tag_count = len(element.find_all())
            link_count = len(element.find_all('a'))
            
            denominator = max(tag_count + link_count * 2, 1)
            density_score = text_length / denominator
            
            if density_score > best_score and text_length > 200:
                best_score = density_score
                best_element = element
        
        return best_element
    
    def _extract_with_trafilatura(self, url: str) -> str:
        """Extract content using trafilatura as fallback"""
        try:
            downloaded = trafilatura.fetch_url(url)
            if downloaded:
                content = trafilatura.extract(downloaded, include_comments=False, include_tables=False)
                return content if content and len(content) > 100 else None
        except Exception:
            pass
        return None
    
    def _is_relevant_content(self, text: str, element) -> bool:
        """Filter out irrelevant content using heuristics"""
        ad_keywords = [
            'advertisement', 'sponsored', 'related articles', 'you may also like',
            'recommended for you', 'trending now', 'more from', 'follow us',
            'share on facebook', 'share on twitter', 'subscribe to',
            'sign up', 'newsletter', 'download our app', 'get notifications'
        ]
        
        text_lower = text.lower()
        if any(keyword in text_lower for keyword in ad_keywords):
            return False
        
        # Check link density
        if element:
            links = element.find_all('a')
            if links:
                link_text_length = sum(len(link.get_text(strip=True)) for link in links)
                total_text_length = len(text)
                if total_text_length > 0 and (link_text_length / total_text_length) > 0.4:
                    return False
        
        # Check for navigation patterns
        nav_patterns = [
            r'^home\s*>',  # Breadcrumb navigation
            r'\d{1,2}:\d{2}\s*(am|pm)$',  # Time stamps only
            r'^\d{1,2}\s+(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)',  # Date only
            r'^share$|^like$|^comment$',  # Social buttons
            r'^\d+\s*(views?|likes?|shares?)$',  # Engagement metrics
        ]
        
        for pattern in nav_patterns:
            if re.search(pattern, text_lower.strip()):
                return False
        
        return True
    
    def _deduplicate_blocks(self, blocks: List[Dict]) -> List[Dict]:
        """Remove duplicate or very similar content blocks"""
        if not blocks:
            return blocks
        
        unique_blocks = []
        seen_texts = set()
        
        for block in blocks:
            text = block['text']
            normalized = re.sub(r'\s+', ' ', text.lower().strip())
            
            is_duplicate = False
            for seen_text in seen_texts:
                if len(normalized) > 0 and len(seen_text) > 0:
                    overlap = len(set(normalized.split()) & set(seen_text.split()))
                    similarity = overlap / max(len(normalized.split()), len(seen_text.split()))
                    if similarity > 0.8:
                        is_duplicate = True
                        break
            
            if not is_duplicate:
                unique_blocks.append(block)
                seen_texts.add(normalized)
        
        return unique_blocks
    
    def _score_text_blocks(self, blocks: List[Dict]) -> List[Dict]:
        """Add quality scores to text blocks"""
        for block in blocks:
            score = self._calculate_content_score(block["text"])
            block.update({
                "score": score,
                "why": self._get_score_reasoning(block["text"], score),
                "section_path": ["article", "main"],
                "heading_ids": [],
                "links": []
            })
        return blocks
    
    def _calculate_content_score(self, text: str) -> float:
        """Calculate content quality score based on multiple factors"""
        score = 0.5  # Base score
        
        # Length factor
        if len(text) > 200:
            score += 0.2
        elif len(text) > 100:
            score += 0.1
        
        # Sentence structure factor
        sentences = text.split('.')
        if len(sentences) > 2:
            score += 0.1
        
        # Word diversity factor
        words = text.lower().split()
        if len(words) > 0:
            unique_words = len(set(words))
            diversity_ratio = unique_words / len(words)
            if diversity_ratio > 0.7:
                score += 0.1
        
        # Punctuation factor
        if any(char in text for char in '.!?;:'):
            score += 0.05
        
        # Penalize if mostly uppercase
        if len(text) > 20 and sum(1 for c in text if c.isupper()) / len(text) > 0.5:
            score -= 0.2
        
        return min(score, 1.0)
    
    def _get_score_reasoning(self, text: str, score: float) -> str:
        """Generate reasoning for content score"""
        reasons = []
        
        if len(text) > 200:
            reasons.append("substantial length")
        elif len(text) > 100:
            reasons.append("adequate length")
        
        if len(text.split('.')) > 2:
            reasons.append("multiple sentences")
        
        words = text.lower().split()
        if len(words) > 0:
            unique_words = len(set(words))
            diversity_ratio = unique_words / len(words)
            if diversity_ratio > 0.7:
                reasons.append("diverse vocabulary")
        
        if not reasons:
            reasons.append("basic content")
        
        return f"Score {score:.2f}: {', '.join(reasons)}"
    
    def _get_extraction_strategy(self, blocks: List[Dict]) -> str:
        """Determine which extraction strategy was used"""
        if not blocks:
            return "none"
        
        methods = set(block.get("extraction_method", "unknown") for block in blocks)
        if len(methods) == 1:
            return list(methods)[0]
        else:
            return "hybrid"
    
    def _calculate_overall_quality(self, blocks: List[Dict]) -> float:
        """Calculate overall quality score for extracted content"""
        if not blocks:
            return 0.0
        
        scores = [block.get("score", 0.5) for block in blocks]
        return sum(scores) / len(scores)
    
    def _get_input_schema(self) -> Dict[str, Any]:
        """Define input schema for Strands SDK"""
        return {
            "type": "object",
            "properties": {
                "soup": {
                    "description": "BeautifulSoup parsed HTML object"
                },
                "url": {
                    "type": "string",
                    "description": "Source URL for context"
                }
            },
            "required": ["soup", "url"]
        }