"""
Credibility Checker tool for assessing source credibility and trustworthiness.
"""

import re
from datetime import datetime
from typing import Dict, Any
from urllib.parse import urlparse

from .base_tool import BaseTool


class CredibilityChecker(BaseTool):
    """Tool for assessing source credibility using domain analysis and heuristics"""
    
    def __init__(self):
        super().__init__(
            name="CredibilityChecker",
            description="Assesses source credibility using domain analysis and external verification patterns"
        )
    
    def execute(self, url: str) -> Dict[str, Any]:
        """
        Check source credibility for a given URL
        
        Args:
            url: URL to assess for credibility
            
        Returns:
            Dict containing credibility assessment
        """
        self._log_execution()
        
        try:
            # Perform domain analysis
            domain_analysis = self._analyze_domain(url)
            
            # Perform mock external verification
            external_verification = self._mock_external_verification(url)
            
            # Calculate overall credibility score
            domain_score = domain_analysis["trust_score"]
            external_score = external_verification.get("credibility_score", 0.5)
            
            # Weighted average (60% external, 40% domain analysis)
            overall_score = (external_score * 0.6) + (domain_score * 0.4)
            
            # Collect all risk factors
            risk_factors = (
                domain_analysis["risk_factors"] + 
                external_verification.get("warnings", [])
            )
            
            # Generate credibility summary
            credibility_notes = self._generate_credibility_summary({
                "overall_score": overall_score,
                "domain_analysis": domain_analysis,
                "external_verification": external_verification,
                "risk_factors": risk_factors
            })
            
            return {
                "success": True,
                "credibility_report": {
                    "domain_analysis": domain_analysis,
                    "external_verification": external_verification,
                    "overall_score": round(overall_score, 2),
                    "risk_factors": risk_factors,
                    "credibility_notes": credibility_notes,
                    "assessment_timestamp": datetime.utcnow().isoformat() + "Z"
                }
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "credibility_report": {
                    "overall_score": 0.5,
                    "risk_factors": ["Assessment failed"],
                    "credibility_notes": f"Credibility assessment failed: {str(e)}"
                }
            }
    
    def _analyze_domain(self, url: str) -> Dict[str, Any]:
        """Analyze domain characteristics for credibility indicators"""
        domain = urlparse(url).netloc.lower()
        
        # Known high-credibility domains
        trusted_domains = [
            'bbc.com', 'reuters.com', 'ap.org', 'npr.org', 'cnn.com',
            'gov.sg', 'moh.gov.sg', 'channelnewsasia.com', 'straitstimes.com',
            'anthropic.com', 'openai.com', 'github.com', 'stackoverflow.com',
            'wikipedia.org', 'nature.com', 'science.org', 'nejm.org'
        ]
        
        # Suspicious patterns
        suspicious_patterns = [
            r'\.(tk|ml|ga|cf)$',  # Free domains
            r'(fake|clickbait|buzz|viral)',  # Suspicious keywords
            r'\d{4,}',  # Long numbers in domain
            r'[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}',  # IP addresses
        ]
        
        trust_score = 0.5  # Neutral baseline
        risk_factors = []
        
        # Boost for trusted domains
        for trusted in trusted_domains:
            if trusted in domain:
                trust_score += 0.3
                break
        
        # Check for suspicious patterns
        for pattern in suspicious_patterns:
            if re.search(pattern, domain):
                trust_score -= 0.2
                risk_factors.append("Suspicious domain pattern detected")
                break
        
        # Check domain characteristics
        if url.startswith('https://'):
            trust_score += 0.1
        else:
            risk_factors.append("No HTTPS encryption")
        
        # Check for common institutional TLDs
        if any(tld in domain for tld in ['.org', '.edu', '.gov']):
            trust_score += 0.1
        
        # Check for regional news domains
        regional_indicators = ['.sg', '.my', '.au', '.uk', '.ca']
        if any(indicator in domain for indicator in regional_indicators):
            trust_score += 0.05
        
        # Additional boost for established Southeast Asian news sources
        if any(news_source in domain for news_source in ['channelnewsasia', 'straitstimes', 'todayonline']):
            trust_score += 0.15
        
        return {
            "domain": domain,
            "trust_score": max(0.0, min(1.0, trust_score)),
            "risk_factors": risk_factors,
            "domain_category": self._categorize_domain(domain)
        }
    
    def _categorize_domain(self, domain: str) -> str:
        """Categorize the domain type"""
        if any(gov in domain for gov in ['.gov', '.edu']):
            return "institutional"
        elif any(news in domain for news in ['news', 'times', 'post', 'herald', 'guardian']):
            return "news_media"
        elif any(tech in domain for tech in ['github', 'stackoverflow', 'medium']):
            return "tech_platform"
        elif domain.count('.') > 2:  # Subdomain
            return "subdomain"
        else:
            return "general"
    
    def _mock_external_verification(self, url: str) -> Dict[str, Any]:
        """Mock external credibility verification (simulates real API calls)"""
        domain = urlparse(url).netloc.lower()
        
        # Simulate different verification responses based on domain patterns
        if any(trusted in domain for trusted in ['bbc.com', 'reuters.com', 'ap.org', 'channelnewsasia.com', 'straitstimes.com']):
            return {
                "credibility_score": 0.9,
                "bias_rating": "neutral",
                "factual_reporting": "very high",
                "warnings": [],
                "source_type": "mainstream_media",
                "verification_source": "mock_newsguard_api"
            }
        elif any(gov in domain for gov in ['.gov', '.edu']):
            return {
                "credibility_score": 0.85,
                "bias_rating": "neutral", 
                "factual_reporting": "high",
                "warnings": [],
                "source_type": "institutional",
                "verification_source": "mock_domain_analysis"
            }
        elif any(blog in domain for blog in ['medium.com', 'substack.com']):
            return {
                "credibility_score": 0.6,
                "bias_rating": "varies",
                "factual_reporting": "mixed",
                "warnings": ["Individual blog - verify claims independently"],
                "source_type": "blog_platform",
                "verification_source": "mock_content_analysis"
            }
        elif any(social in domain for social in ['facebook.com', 'twitter.com', 'instagram.com']):
            return {
                "credibility_score": 0.4,
                "bias_rating": "varies",
                "factual_reporting": "varies",
                "warnings": ["Social media content - verify independently"],
                "source_type": "social_media",
                "verification_source": "mock_platform_analysis"
            }
        else:
            return {
                "credibility_score": 0.5,
                "bias_rating": "unknown",
                "factual_reporting": "unknown", 
                "warnings": ["Source credibility not established"],
                "source_type": "unknown",
                "verification_source": "mock_default"
            }
    
    def _generate_credibility_summary(self, credibility_report: Dict) -> str:
        """Generate human-readable credibility summary"""
        score = credibility_report["overall_score"]
        domain_info = credibility_report["domain_analysis"]
        external = credibility_report["external_verification"]
        
        # Determine credibility level
        if score >= 0.8:
            level = "High credibility"
        elif score >= 0.6:
            level = "Moderate credibility"  
        elif score >= 0.4:
            level = "Low credibility"
        else:
            level = "Very low credibility"
        
        summary = f"{level} source (score: {score:.2f}/1.0). "
        
        # Add source type information
        if "source_type" in external:
            summary += f"Source type: {external['source_type']}. "
        
        # Add factual reporting assessment
        if "factual_reporting" in external and external["factual_reporting"] != "unknown":
            summary += f"Factual reporting: {external['factual_reporting']}. "
        
        # Add bias information
        if "bias_rating" in external and external["bias_rating"] not in ["unknown", "varies"]:
            summary += f"Bias rating: {external['bias_rating']}. "
        
        # Add risk factors (limit to first 2)
        if credibility_report["risk_factors"]:
            summary += f"Risk factors: {'; '.join(credibility_report['risk_factors'][:2])}."
        
        return summary.strip()
    
    def _get_input_schema(self) -> Dict[str, Any]:
        """Define input schema for Strands SDK"""
        return {
            "type": "object",
            "properties": {
                "url": {
                    "type": "string",
                    "description": "URL to assess for credibility"
                }
            },
            "required": ["url"]
        }