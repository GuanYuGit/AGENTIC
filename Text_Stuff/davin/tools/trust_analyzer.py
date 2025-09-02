"""
Trust Analyzer tool using decorator pattern.
"""

import re
from datetime import datetime
from typing import Dict, Any, List
from urllib.parse import urlparse

from decorators import tool, input_schema


@tool(
    name="TrustAnalyzer",
    description="Comprehensive source credibility and trustworthiness assessment engine"
)
class TrustAnalyzer:
    """Advanced trust and credibility analysis system for web sources"""
    
    def __init__(self):
        self.execution_count = 0
        self.last_execution = None
        self.trust_database = self._initialize_trust_database()
    
    @input_schema(
        url={"type": "string", "required": True, "description": "URL to assess for credibility and trustworthiness"},
        deep_analysis={"type": "boolean", "default": True, "description": "Whether to perform deep trust analysis"},
        include_recommendations={"type": "boolean", "default": True, "description": "Whether to include trust recommendations"}
    )
    def execute(self, url: str, deep_analysis: bool = True, include_recommendations: bool = True) -> Dict[str, Any]:
        """
        Perform comprehensive trust and credibility analysis
        
        Args:
            url: URL to analyze
            deep_analysis: Whether to perform deep analysis
            include_recommendations: Whether to include actionable recommendations
            
        Returns:
            Dict containing comprehensive trust assessment
        """
        self._log_execution()
        
        try:
            # Core trust analysis
            domain_analysis = self._analyze_domain_trust(url)
            content_analysis = self._analyze_content_indicators(url) if deep_analysis else {}
            external_verification = self._perform_external_verification(url)
            
            # Calculate composite trust score
            trust_score = self._calculate_composite_trust_score(
                domain_analysis, content_analysis, external_verification
            )
            
            # Generate trust assessment
            trust_assessment = self._generate_trust_assessment(
                trust_score, domain_analysis, content_analysis, external_verification
            )
            
            # Add recommendations if requested
            recommendations = self._generate_trust_recommendations(
                trust_assessment, domain_analysis
            ) if include_recommendations else {}
            
            return {
                "success": True,
                "trust_report": {
                    "overall_trust_score": trust_score,
                    "trust_level": self._categorize_trust_level(trust_score),
                    "domain_analysis": domain_analysis,
                    "content_analysis": content_analysis,
                    "external_verification": external_verification,
                    "trust_assessment": trust_assessment,
                    "recommendations": recommendations,
                    "analysis_metadata": {
                        "analyzed_at": datetime.utcnow().isoformat() + "Z",
                        "analysis_depth": "deep" if deep_analysis else "standard",
                        "analyzer_version": "1.0"
                    }
                }
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "trust_report": {
                    "overall_trust_score": 0.5,
                    "trust_level": "unknown",
                    "error_details": str(e)
                }
            }
    
    def _initialize_trust_database(self) -> Dict[str, Any]:
        """Initialize trust database with known sources"""
        return {
            "highly_trusted": {
                "news_organizations": [
                    'bbc.com', 'reuters.com', 'ap.org', 'npr.org', 
                    'channelnewsasia.com', 'straitstimes.com', 'economist.com',
                    'wsj.com', 'ft.com', 'guardian.com'
                ],
                "institutional": [
                    'gov.sg', 'moh.gov.sg', 'who.int', 'cdc.gov',
                    'europa.eu', 'un.org', 'worldbank.org'
                ],
                "academic": [
                    'nature.com', 'science.org', 'nejm.org', 'lancet.com',
                    'pubmed.ncbi.nlm.nih.gov', 'scholar.google.com'
                ],
                "technology": [
                    'github.com', 'stackoverflow.com', 'arxiv.org',
                    'ieee.org', 'acm.org'
                ]
            },
            "questionable_patterns": [
                r'\.(tk|ml|ga|cf|gq)$',  # Free domains
                r'(fake|clickbait|buzz|viral|scam)',
                r'\d{4,}',  # Numeric domains
                r'[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}',  # IP addresses
                r'(-).*(-)',  # Multiple hyphens
                r'(free|cheap|best|top|amazing|incredible|shocking)',  # Clickbait indicators
            ],
            "trust_indicators": {
                "positive": [
                    'https', 'privacy-policy', 'terms-of-service', 'contact-us',
                    'about-us', 'editorial-guidelines', 'fact-check'
                ],
                "negative": [
                    'popup', 'auto-play', 'clickbait', 'sponsored-content',
                    'affiliate-links', 'gambling', 'adult-content'
                ]
            }
        }
    
    def _analyze_domain_trust(self, url: str) -> Dict[str, Any]:
        """Comprehensive domain trust analysis"""
        domain = urlparse(url).netloc.lower()
        
        analysis = {
            "domain": domain,
            "trust_factors": [],
            "risk_factors": [],
            "domain_category": "unknown",
            "domain_age_estimate": "unknown",
            "ssl_status": "https" if url.startswith('https://') else "http"
        }
        
        # Check against trusted sources
        trust_category = self._categorize_trusted_domain(domain)
        if trust_category:
            analysis["domain_category"] = trust_category
            analysis["trust_factors"].append(f"Listed in {trust_category} trusted sources")
        
        # Check for questionable patterns
        risk_patterns = self._check_risk_patterns(domain, url)
        if risk_patterns:
            analysis["risk_factors"].extend(risk_patterns)
        
        # Domain structure analysis
        domain_structure = self._analyze_domain_structure(domain)
        analysis.update(domain_structure)
        
        # SSL and security indicators
        security_analysis = self._analyze_security_indicators(url)
        analysis.update(security_analysis)
        
        # Calculate domain trust score
        analysis["domain_trust_score"] = self._calculate_domain_trust_score(analysis)
        
        return analysis
    
    def _categorize_trusted_domain(self, domain: str) -> str:
        """Categorize domain based on trusted source lists"""
        trusted_db = self.trust_database["highly_trusted"]
        
        for category, domains in trusted_db.items():
            for trusted_domain in domains:
                if trusted_domain in domain or domain in trusted_domain:
                    return category
        
        return None
    
    def _check_risk_patterns(self, domain: str, url: str) -> List[str]:
        """Check for risky domain patterns"""
        risk_factors = []
        
        for pattern in self.trust_database["questionable_patterns"]:
            if re.search(pattern, domain, re.IGNORECASE):
                if pattern.startswith(r'\.('):
                    risk_factors.append("Suspicious top-level domain")
                elif 'clickbait' in pattern:
                    risk_factors.append("Contains clickbait indicators")
                elif r'\d{4,}' == pattern:
                    risk_factors.append("Numeric domain name")
                elif 'ip' in pattern.lower():
                    risk_factors.append("IP address instead of domain")
                else:
                    risk_factors.append("Suspicious domain pattern")
                break
        
        return risk_factors
    
    def _analyze_domain_structure(self, domain: str) -> Dict[str, Any]:
        """Analyze domain structure for trust indicators"""
        parts = domain.split('.')
        
        analysis = {
            "subdomain_count": len(parts) - 2 if len(parts) > 2 else 0,
            "tld": parts[-1] if parts else "unknown",
            "domain_length": len(domain),
            "has_subdomain": len(parts) > 2
        }
        
        # TLD analysis
        trusted_tlds = ['.gov', '.edu', '.org', '.mil']
        commercial_tlds = ['.com', '.co', '.biz', '.info']
        regional_tlds = ['.sg', '.uk', '.au', '.ca', '.eu']
        
        if any(tld in domain for tld in trusted_tlds):
            analysis["tld_category"] = "institutional"
            analysis["tld_trust_bonus"] = 0.2
        elif any(tld in domain for tld in commercial_tlds):
            analysis["tld_category"] = "commercial"
            analysis["tld_trust_bonus"] = 0.0
        elif any(tld in domain for tld in regional_tlds):
            analysis["tld_category"] = "regional"
            analysis["tld_trust_bonus"] = 0.1
        else:
            analysis["tld_category"] = "other"
            analysis["tld_trust_bonus"] = -0.1
        
        # Domain length analysis
        if analysis["domain_length"] > 50:
            analysis["length_concern"] = "Very long domain name"
        elif analysis["domain_length"] < 5:
            analysis["length_concern"] = "Very short domain name"
        
        return analysis
    
    def _analyze_security_indicators(self, url: str) -> Dict[str, Any]:
        """Analyze security indicators"""
        analysis = {
            "uses_https": url.startswith('https://'),
            "security_score": 0.0,
            "security_factors": []
        }
        
        if analysis["uses_https"]:
            analysis["security_score"] += 0.3
            analysis["security_factors"].append("Uses HTTPS encryption")
        else:
            analysis["security_factors"].append("WARNING: Uses unencrypted HTTP")
            analysis["security_score"] -= 0.2
        
        return analysis
    
    def _analyze_content_indicators(self, url: str) -> Dict[str, Any]:
        """Analyze content-based trust indicators"""
        # This is a placeholder for content analysis
        # In a full implementation, this would analyze page content
        
        return {
            "content_quality_score": 0.7,  # Placeholder
            "content_indicators": [
                "Standard content analysis not implemented",
                "Placeholder trust indicators"
            ],
            "readability_score": "unknown",
            "fact_check_presence": False,
            "author_information": "unknown",
            "publication_date": "unknown",
            "sources_cited": "unknown"
        }
    
    def _perform_external_verification(self, url: str) -> Dict[str, Any]:
        """Perform external verification checks"""
        domain = urlparse(url).netloc.lower()
        
        # Simulate external API checks (placeholder for real implementation)
        verification = {
            "malware_status": "clean",
            "phishing_status": "clean", 
            "spam_status": "clean",
            "blacklist_status": "clean",
            "reputation_score": 0.7,  # Placeholder
            "verification_sources": ["simulated_check"],
            "last_verified": datetime.utcnow().isoformat() + "Z"
        }
        
        # Domain-specific verification
        if any(trusted in domain for trusted in ['bbc.com', 'reuters.com', 'gov.sg']):
            verification.update({
                "malware_status": "verified_clean",
                "reputation_score": 0.95,
                "trust_seal": "high_authority"
            })
        elif any(suspicious in domain for suspicious in ['.tk', '.ml', 'clickbait']):
            verification.update({
                "reputation_score": 0.2,
                "trust_seal": "caution_advised",
                "risk_indicators": ["suspicious_domain_pattern"]
            })
        
        return verification
    
    def _calculate_composite_trust_score(self, domain_analysis: Dict, content_analysis: Dict, external_verification: Dict) -> float:
        """Calculate composite trust score"""
        # Weight the different analysis components
        domain_weight = 0.4
        content_weight = 0.3
        external_weight = 0.3
        
        # Get individual scores
        domain_score = domain_analysis.get("domain_trust_score", 0.5)
        content_score = content_analysis.get("content_quality_score", 0.5)
        external_score = external_verification.get("reputation_score", 0.5)
        
        # Calculate weighted average
        composite_score = (domain_score * domain_weight) + \
                         (content_score * content_weight) + \
                         (external_score * external_weight)
        
        return round(max(0.0, min(1.0, composite_score)), 3)
    
    def _calculate_domain_trust_score(self, analysis: Dict) -> float:
        """Calculate domain-specific trust score"""
        base_score = 0.5
        
        # Category bonuses
        category_bonuses = {
            "news_organizations": 0.3,
            "institutional": 0.35,
            "academic": 0.4,
            "technology": 0.25
        }
        
        category = analysis.get("domain_category", "unknown")
        if category in category_bonuses:
            base_score += category_bonuses[category]
        
        # TLD bonus
        base_score += analysis.get("tld_trust_bonus", 0)
        
        # Security bonus
        if analysis.get("uses_https", False):
            base_score += 0.1
        
        # Risk factor penalties
        risk_count = len(analysis.get("risk_factors", []))
        base_score -= (risk_count * 0.15)
        
        return max(0.0, min(1.0, base_score))
    
    def _categorize_trust_level(self, score: float) -> str:
        """Categorize trust level based on score"""
        if score >= 0.8:
            return "highly_trusted"
        elif score >= 0.65:
            return "trusted"
        elif score >= 0.5:
            return "moderate_trust"
        elif score >= 0.3:
            return "low_trust"
        else:
            return "untrusted"
    
    def _generate_trust_assessment(self, trust_score: float, domain_analysis: Dict, content_analysis: Dict, external_verification: Dict) -> Dict[str, Any]:
        """Generate comprehensive trust assessment"""
        trust_level = self._categorize_trust_level(trust_score)
        
        assessment = {
            "trust_level": trust_level,
            "confidence": self._calculate_confidence_level(domain_analysis, external_verification),
            "primary_trust_factors": [],
            "primary_risk_factors": [],
            "overall_recommendation": ""
        }
        
        # Collect primary trust factors
        if domain_analysis.get("domain_category") in ["news_organizations", "institutional", "academic"]:
            assessment["primary_trust_factors"].append(f"Recognized {domain_analysis['domain_category']} source")
        
        if domain_analysis.get("uses_https"):
            assessment["primary_trust_factors"].append("Secure HTTPS connection")
        
        if external_verification.get("reputation_score", 0) > 0.8:
            assessment["primary_trust_factors"].append("High external reputation score")
        
        # Collect primary risk factors
        risk_factors = domain_analysis.get("risk_factors", [])
        if risk_factors:
            assessment["primary_risk_factors"].extend(risk_factors[:3])  # Top 3 risks
        
        if not domain_analysis.get("uses_https", True):
            assessment["primary_risk_factors"].append("Unencrypted HTTP connection")
        
        # Generate recommendation
        assessment["overall_recommendation"] = self._generate_overall_recommendation(trust_level, assessment)
        
        return assessment
    
    def _calculate_confidence_level(self, domain_analysis: Dict, external_verification: Dict) -> str:
        """Calculate confidence in the trust assessment"""
        confidence_factors = 0
        
        # High confidence factors
        if domain_analysis.get("domain_category") != "unknown":
            confidence_factors += 1
        
        if external_verification.get("reputation_score", 0) != 0.5:  # Not default
            confidence_factors += 1
        
        if domain_analysis.get("risk_factors"):
            confidence_factors += 1
        
        if confidence_factors >= 2:
            return "high"
        elif confidence_factors == 1:
            return "medium"
        else:
            return "low"
    
    def _generate_overall_recommendation(self, trust_level: str, assessment: Dict) -> str:
        """Generate overall trust recommendation"""
        recommendations = {
            "highly_trusted": "This source appears highly trustworthy. Content can be considered reliable.",
            "trusted": "This source appears trustworthy. Content is likely reliable with standard verification.",
            "moderate_trust": "This source has moderate trustworthiness. Verify important claims independently.",
            "low_trust": "This source has low trustworthiness. Exercise caution and verify claims from multiple sources.",
            "untrusted": "This source appears untrustworthy. Avoid relying on this content without strong verification."
        }
        
        base_recommendation = recommendations.get(trust_level, "Unknown trustworthiness level.")
        
        # Add specific warnings if needed
        if assessment.get("primary_risk_factors"):
            base_recommendation += f" Note: {assessment['primary_risk_factors'][0]}"
        
        return base_recommendation
    
    def _generate_trust_recommendations(self, trust_assessment: Dict, domain_analysis: Dict) -> Dict[str, Any]:
        """Generate actionable trust recommendations"""
        recommendations = {
            "immediate_actions": [],
            "verification_steps": [],
            "red_flags_to_watch": [],
            "trust_building_indicators": []
        }
        
        trust_level = trust_assessment["trust_level"]
        
        # Immediate actions based on trust level
        if trust_level in ["untrusted", "low_trust"]:
            recommendations["immediate_actions"].extend([
                "Cross-reference claims with trusted sources",
                "Check author credentials and publication date",
                "Look for cited sources and references"
            ])
        elif trust_level == "moderate_trust":
            recommendations["immediate_actions"].extend([
                "Verify key claims independently",
                "Check for recent updates or corrections"
            ])
        
        # Verification steps
        if not domain_analysis.get("uses_https"):
            recommendations["verification_steps"].append("Verify site security before entering personal information")
        
        recommendations["verification_steps"].extend([
            "Check domain registration information",
            "Look for contact information and editorial policies",
            "Verify author expertise in the subject matter"
        ])
        
        # Red flags
        if domain_analysis.get("risk_factors"):
            recommendations["red_flags_to_watch"].extend([
                "Suspicious domain characteristics detected",
                "Unusual URL patterns or structures"
            ])
        
        # Trust building indicators to look for
        recommendations["trust_building_indicators"].extend([
            "Editorial guidelines and fact-checking policies",
            "Clear author information and credentials",
            "Regular updates and error corrections",
            "Transparent funding and ownership information"
        ])
        
        return recommendations
    
    def _log_execution(self):
        """Log tool execution"""
        self.execution_count += 1
        self.last_execution = datetime.utcnow().isoformat() + "Z"