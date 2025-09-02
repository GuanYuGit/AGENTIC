"""
Intelligence Engine tool using decorator pattern - handles all LLM and Vision analysis.
"""

import os
import json
import base64
import hashlib
import boto3
import requests
from typing import Dict, Any, List, Optional
from dotenv import load_dotenv

from decorators import tool, input_schema

load_dotenv()


@tool(
    name="IntelligenceEngine",
    description="Advanced AI analysis engine for content validation, image analysis, and text processing using LLMs and Vision models"
)
class IntelligenceEngine:
    """Unified AI intelligence engine for content analysis and validation"""
    
    def __init__(self):
        self.bedrock_client = boto3.client(
            'bedrock-runtime',
            aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
            aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'),
            region_name=os.getenv('AWS_REGION', 'us-east-1')
        )
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        self.default_model = "anthropic.claude-3-haiku-20240307-v1:0"
        self.execution_count = 0
        self.last_execution = None
    
    @input_schema(
        analysis_type={"type": "string", "enum": ["content_validation", "image_analysis", "text_scoring", "structure_analysis"], "required": True, "description": "Type of AI analysis to perform"},
        content={"description": "Content to analyze (text, image data, or structured content)", "required": True},
        context={"type": "object", "default": {}, "description": "Additional context for analysis"},
        model_config={"type": "object", "default": {}, "description": "Model configuration (temperature, max_tokens, etc.)"}
    )
    def execute(self, analysis_type: str, content: Any, context: Dict = None, model_config: Dict = None) -> Dict[str, Any]:
        """
        Execute AI analysis using appropriate models
        
        Args:
            analysis_type: Type of analysis ('content_validation', 'image_analysis', 'text_scoring', 'structure_analysis')
            content: Content to analyze
            context: Additional context information
            model_config: Model configuration parameters
            
        Returns:
            Dict containing analysis results
        """
        self._log_execution()
        
        try:
            context = context or {}
            model_config = model_config or {}
            
            # Route to appropriate analysis method
            if analysis_type == "content_validation":
                return self._analyze_content_validation(content, context, model_config)
            elif analysis_type == "image_analysis":
                return self._analyze_image_relevance(content, context, model_config)
            elif analysis_type == "text_scoring":
                return self._analyze_text_scoring(content, context, model_config)
            elif analysis_type == "structure_analysis":
                return self._analyze_page_structure(content, context, model_config)
            else:
                return {
                    "success": False,
                    "error": f"Unsupported analysis type: {analysis_type}"
                }
                
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "analysis_type": analysis_type
            }
    
    def _analyze_content_validation(self, content: str, context: Dict, model_config: Dict) -> Dict[str, Any]:
        """Analyze content for coherence and validation"""
        prompt = self._build_content_validation_prompt(content, context)
        
        llm_result = self._call_text_model(
            prompt=prompt,
            max_tokens=model_config.get('max_tokens', 200),
            temperature=model_config.get('temperature', 0.1)
        )
        
        if not llm_result["success"]:
            return llm_result
        
        # Parse the validation response
        parsed_result = self._parse_content_validation_response(
            llm_result["response"], 
            context.get('total_chunks', 0)
        )
        
        return {
            "success": True,
            "analysis_type": "content_validation",
            "raw_response": llm_result["response"],
            "parsed_result": parsed_result,
            "analysis_metadata": {
                "model_used": llm_result["model_id"],
                "prompt_length": len(prompt),
                "response_length": len(llm_result["response"])
            }
        }
    
    def _analyze_image_relevance(self, images: List[Dict], context: Dict, model_config: Dict) -> Dict[str, Any]:
        """Analyze images for relevance using vision model"""
        if not images:
            return {
                "success": True,
                "analysis_type": "image_analysis",
                "relevant_images": [],
                "analysis_stats": {"total_images": 0, "relevant_count": 0}
            }
        
        article_context = context.get('article_context', '')
        base_url = context.get('base_url', '')
        
        relevant_images = []
        analysis_stats = {
            "total_images": len(images),
            "analyzed_count": 0,
            "relevant_count": 0,
            "download_failures": 0,
            "analysis_failures": 0
        }
        
        for img in images:
            try:
                # Analyze individual image
                result = self._analyze_single_image(img, article_context, base_url, model_config)
                
                if result["success"]:
                    analysis_stats["analyzed_count"] += 1
                    if result["analysis"]["is_relevant"]:
                        analysis_stats["relevant_count"] += 1
                        relevant_images.append(self._create_relevant_image_record(img, result["analysis"]))
                    else:
                        print(f"✗ Image rejected by AI: {img['src'][:60]}... | {result['analysis'].get('reasoning', 'No reason')}")
                else:
                    analysis_stats["analysis_failures"] += 1
                    print(f"✗ Image analysis failed: {img['src'][:60]}... | {result.get('error', 'Unknown error')}")
                        
            except Exception as e:
                analysis_stats["analysis_failures"] += 1
                print(f"Error analyzing image {img.get('src', 'unknown')}: {e}")
        
        return {
            "success": True,
            "analysis_type": "image_analysis",
            "relevant_images": relevant_images,
            "analysis_stats": analysis_stats
        }
    
    def _analyze_text_scoring(self, text_blocks: List[Dict], context: Dict, model_config: Dict) -> Dict[str, Any]:
        """Score text blocks for relevance"""
        guidance = context.get('guidance', 'Focus on main content areas, article text, and informative content.')
        scored_blocks = []
        
        for block in text_blocks:
            if len(block.get("text", "")) < 100:  # Skip very short blocks
                continue
                
            try:
                prompt = self._build_text_scoring_prompt(block["text"], guidance)
                
                llm_result = self._call_text_model(
                    prompt=prompt,
                    max_tokens=model_config.get('max_tokens', 50),
                    temperature=model_config.get('temperature', 0.1)
                )
                
                if llm_result["success"]:
                    parsed_score = self._parse_text_scoring_response(llm_result["response"])
                    
                    if parsed_score["relevance_decision"]:
                        enhanced_block = block.copy()
                        enhanced_block.update({
                            "score": parsed_score["score"],
                            "why": parsed_score["reason"],
                            "section_path": ["article", "main"],
                            "heading_ids": [],
                            "links": []
                        })
                        scored_blocks.append(enhanced_block)
                        
            except Exception as e:
                # Fallback for scoring failures
                if len(block.get("text", "")) > 200:
                    enhanced_block = block.copy()
                    enhanced_block.update({
                        "score": 0.7,
                        "why": f"Fallback: substantial content (LLM failed: {str(e)})",
                        "section_path": ["article", "main"],
                        "heading_ids": [],
                        "links": []
                    })
                    scored_blocks.append(enhanced_block)
        
        return {
            "success": True,
            "analysis_type": "text_scoring", 
            "scored_blocks": scored_blocks,
            "analysis_metadata": {
                "original_blocks": len(text_blocks),
                "scored_blocks": len(scored_blocks),
                "scoring_method": "llm_with_fallback"
            }
        }
    
    def _analyze_page_structure(self, html_content: str, context: Dict, model_config: Dict) -> Dict[str, Any]:
        """Analyze HTML structure for content extraction guidance"""
        prompt = f"""Analyze this HTML structure and identify the main content areas that contain valuable information.
Focus on:
- Primary article/content body
- Main headings and text sections  
- Relevant images and figures
- Avoid navigation, ads, sidebars, footers

HTML sample:
{html_content[:3000]}

Provide guidance on what content to prioritize for extraction."""
        
        llm_result = self._call_text_model(
            prompt=prompt,
            max_tokens=model_config.get('max_tokens', 300),
            temperature=model_config.get('temperature', 0.7)
        )
        
        if llm_result["success"]:
            return {
                "success": True,
                "analysis_type": "structure_analysis",
                "guidance": llm_result["response"],
                "analysis_metadata": {
                    "model_used": llm_result["model_id"],
                    "html_sample_length": len(html_content[:3000])
                }
            }
        else:
            return {
                "success": False,
                "analysis_type": "structure_analysis",
                "error": llm_result["error"],
                "guidance": "Focus on main content areas, article text, and informative images."
            }
    
    def _analyze_single_image(self, img: Dict, article_context: str, base_url: str, model_config: Dict) -> Dict[str, Any]:
        """Analyze single image for relevance using vision model"""
        try:
            # Download and encode image
            image_data = self._download_and_encode_image(img["src"], model_config.get('max_image_size_mb', 3))
            if not image_data:
                return {"success": False, "error": "Failed to download or encode image"}
            
            # Create vision analysis prompt
            prompt = self._build_image_analysis_prompt(img, article_context, base_url)
            
            # Call vision model
            vision_result = self._call_vision_model(
                prompt=prompt,
                image_data=image_data,
                max_tokens=model_config.get('max_tokens', 300),
                temperature=model_config.get('temperature', 0.1)
            )
            
            if vision_result["success"]:
                # Parse vision response
                analysis = self._parse_vision_response(vision_result["response"])
                return {"success": True, "analysis": analysis}
            else:
                return {"success": False, "error": vision_result["error"]}
                
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _call_text_model(self, prompt: str, max_tokens: int = 200, temperature: float = 0.1, model_id: str = None) -> Dict[str, Any]:
        """Call text-based LLM model"""
        try:
            model_id = model_id or self.default_model
            
            body = json.dumps({
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": max_tokens,
                "temperature": temperature,
                "messages": [{"role": "user", "content": prompt}]
            })
            
            response = self.bedrock_client.invoke_model(
                modelId=model_id,
                body=body,
                contentType="application/json",
                accept="application/json"
            )
            
            response_body = json.loads(response['body'].read())
            result = response_body['content'][0]['text'].strip()
            
            return {
                "success": True,
                "response": result,
                "model_id": model_id
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "model_id": model_id or self.default_model
            }
    
    def _call_vision_model(self, prompt: str, image_data: str, max_tokens: int = 300, temperature: float = 0.1, model_id: str = None) -> Dict[str, Any]:
        """Call vision-enabled model"""
        try:
            model_id = model_id or self.default_model
            
            body = json.dumps({
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": max_tokens,
                "temperature": temperature,
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {
                                "type": "image",
                                "source": {
                                    "type": "base64",
                                    "media_type": "image/jpeg",
                                    "data": image_data
                                }
                            }
                        ]
                    }
                ]
            })
            
            response = self.bedrock_client.invoke_model(
                modelId=model_id,
                body=body,
                contentType="application/json"
            )
            
            response_body = json.loads(response['body'].read())
            result = response_body['content'][0]['text'].strip()
            
            return {
                "success": True,
                "response": result,
                "model_id": model_id
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "model_id": model_id or self.default_model
            }
    
    def _download_and_encode_image(self, image_url: str, max_size_mb: int = 3) -> Optional[str]:
        """Download and encode image as base64"""
        try:
            response = self.session.get(image_url, timeout=10, stream=True)
            response.raise_for_status()
            
            # Check content length
            content_length = response.headers.get('content-length')
            if content_length and int(content_length) > max_size_mb * 1024 * 1024:
                return None
            
            # Read image data with size limit
            image_data = b""
            downloaded = 0
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    downloaded += len(chunk)
                    if downloaded > max_size_mb * 1024 * 1024:
                        return None
                    image_data += chunk
            
            return base64.b64encode(image_data).decode('utf-8')
            
        except Exception:
            return None
    
    # Prompt building methods
    def _build_content_validation_prompt(self, content: str, context: Dict) -> str:
        """Build prompt for content validation"""
        url = context.get('url', '')
        
        return f"""Analyze this extracted web content for coherence and relevance. Apply balanced filtering - keep main content, remove obvious noise.

URL: {url}

CONTENT TO VALIDATE:
{content[:3000]}

Instructions:
1. Identify the main topic/theme of the content
2. Evaluate each CHUNK using these criteria:
   - KEEP: Main article content, core information, relevant details
   - REMOVE: Navigation menus, ads, "related articles", social sharing buttons, author bios, cookie notices, subscription prompts
3. Use balanced judgment - not too strict, not too lenient
4. If 80%+ of chunks are relevant main content, keep all major chunks
5. Only remove chunks that are clearly peripheral or promotional

Evaluation criteria for each chunk:
- Is this part of the main article/story?
- Does this provide information about the main topic?
- Or is this website navigation/promotion/sidebar content?

Respond in this exact format:
MAIN_THEME: [brief description of the main content theme]
MOSTLY_RELEVANT: [YES/NO - are 80%+ of chunks main content?]
KEEP_CHUNKS: [comma-separated list of chunk numbers to keep, e.g., "1,2,4,5"]
REMOVED_REASON: [brief explanation of what types of content were filtered out]"""
    
    def _build_text_scoring_prompt(self, text: str, guidance: str) -> str:
        """Build prompt for text scoring"""
        return f"""Rate the relevance of this text content (1-10) based on whether it represents main valuable information:

Guidance: {guidance}

Text: {text[:500]}

Respond with just: SCORE|REASON
Example: 8|Contains main article content with key information"""
    
    def _build_image_analysis_prompt(self, img: Dict, article_context: str, base_url: str) -> str:
        """Build prompt for image analysis"""
        return f"""Analyze this image to determine if it directly illustrates the main article content or if it's just a generic/stock image.

ARTICLE TEXT: {article_context[:1000]}

ARTICLE URL: {base_url}
IMAGE ALT TEXT: {img.get('alt', 'None')}
IMAGE CONTEXT: {img.get('context', {}).get('surrounding_text', 'None')[:200]}

CRITICAL EVALUATION CRITERIA:
1. Does this image DIRECTLY illustrate specific events, people, objects, or concepts mentioned in the article?
2. Is this a generic stock photo, company logo, or decorative image that could appear on any article?
3. Would removing this image reduce understanding of the article's specific content?

REJECT if the image is:
- Generic stock photos (people working, handshakes, abstract concepts)
- Company logos or branding images
- Decorative headers/footers
- Social media icons or navigation elements
- Images that could apply to any similar topic

ACCEPT only if the image:
- Shows specific people, places, or events mentioned in the article
- Illustrates unique data, charts, or diagrams from the content
- Depicts the actual subject matter being discussed

Respond in this exact format:
RELEVANT: [YES/NO - be very strict, err on NO]
DESCRIPTION: [What exactly does the image show?]
ROLE: [figure/photo/illustration/diagram/chart/other]
RELEVANCE_SCORE: [0.0-1.0 - use 0.8+ only for clearly article-specific images]
REASONING: [Why is this specific to this article vs generic?]"""
    
    # Response parsing methods
    def _parse_content_validation_response(self, response: str, total_chunks: int) -> Dict[str, Any]:
        """Parse content validation response"""
        mostly_relevant = False
        keep_indices = []
        main_theme = ""
        removed_reason = ""
        
        try:
            lines = response.split('\n')
            
            for line in lines:
                line = line.strip()
                if line.startswith('MAIN_THEME:'):
                    main_theme = line.split(':', 1)[1].strip()
                elif line.startswith('MOSTLY_RELEVANT:'):
                    relevant_str = line.split(':', 1)[1].strip().upper()
                    mostly_relevant = relevant_str == "YES"
                elif line.startswith('KEEP_CHUNKS:'):
                    chunks_str = line.split(':', 1)[1].strip()
                    for chunk_num in chunks_str.split(','):
                        chunk_num = chunk_num.strip()
                        if chunk_num.isdigit():
                            idx = int(chunk_num) - 1
                            if 0 <= idx < total_chunks:
                                keep_indices.append(idx)
                elif line.startswith('REMOVED_REASON:'):
                    removed_reason = line.split(':', 1)[1].strip()
            
            # Fallback logic
            if not keep_indices:
                keep_indices = list(range(min(int(total_chunks * 0.75), total_chunks)))
                
        except Exception:
            mostly_relevant = False
            keep_indices = list(range(min(int(total_chunks * 0.75), total_chunks)))
        
        return {
            "main_theme": main_theme,
            "mostly_relevant": mostly_relevant,
            "keep_indices": keep_indices,
            "removed_reason": removed_reason,
            "validation_decision": {
                "keep_count": len(keep_indices),
                "total_count": total_chunks,
                "keep_percentage": len(keep_indices) / total_chunks if total_chunks > 0 else 0
            }
        }
    
    def _parse_text_scoring_response(self, response: str) -> Dict[str, Any]:
        """Parse text scoring response"""
        try:
            if '|' in response:
                score_str, reason = response.split('|', 1)
                score = float(score_str.strip())
                return {
                    "score": score / 10,  # Normalize to 0-1
                    "reason": reason.strip(),
                    "relevance_decision": score >= 7.0
                }
        except Exception:
            pass
        
        return {
            "score": 0.5,
            "reason": "Failed to parse scoring response",
            "relevance_decision": False
        }
    
    def _parse_vision_response(self, response: str) -> Dict[str, Any]:
        """Parse vision analysis response"""
        try:
            analysis = {
                "is_relevant": False,
                "description": "",
                "role": "content", 
                "relevance_score": 0.0,
                "reasoning": ""
            }
            
            for line in response.split('\n'):
                line = line.strip()
                if line.startswith('RELEVANT:'):
                    relevant = line.split(':', 1)[1].strip().upper()
                    analysis["is_relevant"] = relevant == "YES"
                elif line.startswith('DESCRIPTION:'):
                    analysis["description"] = line.split(':', 1)[1].strip()
                elif line.startswith('ROLE:'):
                    analysis["role"] = line.split(':', 1)[1].strip().lower()
                elif line.startswith('RELEVANCE_SCORE:'):
                    try:
                        score = float(line.split(':', 1)[1].strip())
                        analysis["relevance_score"] = max(0.0, min(1.0, score))
                    except ValueError:
                        analysis["relevance_score"] = 0.5
                elif line.startswith('REASONING:'):
                    analysis["reasoning"] = line.split(':', 1)[1].strip()
            
            # Override relevance if score is too low
            if analysis["relevance_score"] < 0.65:
                analysis["is_relevant"] = False
            
            return analysis
            
        except Exception:
            return {
                "is_relevant": False,
                "description": "Analysis failed",
                "role": "content",
                "relevance_score": 0.0,
                "reasoning": "Failed to parse vision response"
            }
    
    def _create_relevant_image_record(self, img: Dict, analysis: Dict) -> Dict[str, Any]:
        """Create enhanced image record for relevant images"""
        img_hash = hashlib.sha256(img["src"].encode()).hexdigest()[:12]
        
        return {
            "id": img["id"],
            "src": img["src"],
            "local_path": f"images/{img_hash}.png",
            "sha256": img_hash,
            "width": img.get("size", {}).get("width"),
            "height": img.get("size", {}).get("height"),
            "format": "png",
            "role": analysis.get('role', 'content'),
            "alt": img["alt"],
            "caption": analysis.get('description', img["alt"]),
            "context_text": img.get("context", {}).get("surrounding_text", ""),
            "score": analysis.get('relevance_score', 0.7),
            "why": analysis.get('reasoning', 'AI analysis: relevant to content'),
            "ai_analysis": analysis
        }
    
    def _log_execution(self):
        """Log tool execution"""
        from datetime import datetime
        self.execution_count += 1
        self.last_execution = datetime.utcnow().isoformat() + "Z"