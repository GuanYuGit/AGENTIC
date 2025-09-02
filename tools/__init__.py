"""
Tools package - Modular components for web scraping tasks

Tools are focused, single-responsibility components that handle specific
aspects of web scraping and content processing.

Available Tools:
- WebFetcher: HTML content fetching with metadata extraction
- ContentExtractor: Advanced text extraction with multiple strategies  
- MediaExtractor: Image and video extraction with quality analysis
- QualityFilter: Content filtering with configurable strictness
- IntelligenceEngine: AI-powered content analysis and validation
- TrustAnalyzer: Source credibility and trust assessment

Legacy tools are still available for backwards compatibility.
"""

# New decorator-based tools
from .web_fetcher import WebFetcher
from .content_extractor import ContentExtractor
from .media_extractor import MediaExtractor
from .quality_filter import QualityFilter
from .intelligence_engine import IntelligenceEngine
from .trust_analyzer import TrustAnalyzer

# Legacy tools (for backwards compatibility)
from .html_fetcher import HTMLFetcher
from .text_extractor import TextExtractor
from .image_extractor import ImageExtractor
from .content_filter import ContentFilter
from .llm_analyzer import LLMAnalyzer
from .vision_analyzer import VisionAnalyzer
from .credibility_checker import CredibilityChecker

__all__ = [
    # New decorator-based tools
    "WebFetcher",
    "ContentExtractor", 
    "MediaExtractor",
    "QualityFilter",
    "IntelligenceEngine",
    "TrustAnalyzer",
    # Legacy tools
    'HTMLFetcher',
    'TextExtractor', 
    'ImageExtractor',
    'ContentFilter',
    'LLMAnalyzer',
    'VisionAnalyzer',
    'CredibilityChecker'
]