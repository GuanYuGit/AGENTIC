"""
Vision Analyzer tool for image content analysis using vision-enabled LLMs.
"""

import os
import json
import base64
import hashlib
import boto3
import requests
from typing import Dict, Any, List
from dotenv import load_dotenv

from .base_tool import BaseTool

load_dotenv()


class VisionAnalyzer(BaseTool):
    """Tool for analyzing image content using vision-enabled LLMs"""
    
    def __init__(self):
        super().__init__(
            name="VisionAnalyzer",
            description="Analyzes images using vision-enabled LLMs to determine relevance and content"
        )
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
    
    def execute(self, images: List[Dict], article_context: str, base_url: str, **kwargs) -> Dict[str, Any]:
        """
        Analyze images for relevance to article content
        
        Args:
            images: List of image dictionaries to analyze
            article_context: Article text for context
            base_url: Base URL of the article
            **kwargs: Additional parameters
            
        Returns:
            Dict containing analysis results
        """
        self._log_execution()
        
        analyzed_images = []
        analysis_stats = {
            "total_images": len(images),
            "analyzed_count": 0,
            "relevant_count": 0,
            "download_failures": 0,
            "analysis_failures": 0
        }
        
        for img in images:
            try:
                # Analyze the image
                result = self._analyze_single_image(img, article_context, base_url, **kwargs)
                
                if result["success"]:
                    analysis_stats["analyzed_count"] += 1
                    if result["analysis"]["is_relevant"]:
                        analysis_stats["relevant_count"] += 1
                        analyzed_images.append(self._create_relevant_image_record(img, result["analysis"]))
                    else:
                        # Log rejection for debugging
                        print(f"✗ Image rejected by LLM: {img['src'][:60]}... | Reason: {result['analysis'].get('reasoning', 'No reasoning provided')}")
                else:
                    if "download" in result.get("error", "").lower():
                        analysis_stats["download_failures"] += 1
                    else:
                        analysis_stats["analysis_failures"] += 1
                    print(f"✗ Image analysis failed: {img['src'][:60]}... | Error: {result.get('error', 'Unknown error')}")
                        
            except Exception as e:
                analysis_stats["analysis_failures"] += 1
                print(f"Error analyzing image {img.get('src', 'unknown')}: {e}")
        
        return {
            "success": True,
            "relevant_images": analyzed_images,
            "analysis_stats": analysis_stats
        }
    
    def _analyze_single_image(self, img: Dict, article_context: str, base_url: str, **kwargs) -> Dict[str, Any]:
        """Analyze a single image for relevance"""
        try:
            # Download and encode the image
            image_data = self._download_and_encode_image(img["src"], kwargs.get('max_size_mb', 3))
            if not image_data:
                return {"success": False, "error": "Failed to download or encode image"}
            
            # Create the analysis prompt
            prompt = self._create_analysis_prompt(img, article_context, base_url)
            
            # Call the vision model
            model_id = kwargs.get('model_id', self.default_model)
            max_tokens = kwargs.get('max_tokens', 300)
            temperature = kwargs.get('temperature', 0.1)
            
            body = json.dumps({
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": max_tokens,
                "temperature": temperature,
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": prompt
                            },
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
            
            # Parse the response
            analysis = self._parse_vision_response(result)
            
            return {
                "success": True,
                "analysis": analysis,
                "raw_response": result
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _download_and_encode_image(self, image_url: str, max_size_mb: int = 3) -> str:
        """Download image and encode as base64"""
        try:
            response = self.session.get(image_url, timeout=10, stream=True)
            response.raise_for_status()
            
            # Check content length
            content_length = response.headers.get('content-length')
            if content_length and int(content_length) > max_size_mb * 1024 * 1024:
                return None
            
            # Read image data
            image_data = b""
            downloaded = 0
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    downloaded += len(chunk)
                    if downloaded > max_size_mb * 1024 * 1024:
                        return None
                    image_data += chunk
            
            # Encode as base64
            return base64.b64encode(image_data).decode('utf-8')
            
        except Exception:
            return None
    
    def _create_analysis_prompt(self, img: Dict, article_context: str, base_url: str) -> str:
        """Create the vision analysis prompt"""
        return f"""Analyze this image to determine if it directly illustrates the main article content or if it's just a generic/stock image.

ARTICLE TEXT: {article_context[:1000]}

ARTICLE URL: {base_url}
IMAGE ALT TEXT: {img.get('alt', 'None')}
IMAGE CONTEXT: {img.get('context_text', 'None')[:200]}

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
    
    def _parse_vision_response(self, response: str) -> Dict[str, Any]:
        """Parse the vision analysis response"""
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
        """Create a complete image record for relevant images"""
        img_hash = hashlib.sha256(img["src"].encode()).hexdigest()[:12]
        
        return {
            "id": img["id"],
            "src": img["src"],
            "local_path": f"images/{img_hash}.png",
            "sha256": img_hash,
            "width": img.get("width"),
            "height": img.get("height"),
            "format": "png",
            "role": analysis.get('role', 'content'),
            "alt": img["alt"],
            "caption": analysis.get('description', img["alt"]),
            "context_text": img["context_text"],
            "score": analysis.get('relevance_score', 0.7),
            "why": analysis.get('reasoning', 'Vision analysis: relevant to content'),
            "vision_analysis": analysis
        }
    
    def _get_input_schema(self) -> Dict[str, Any]:
        """Define input schema for Strands SDK"""
        return {
            "type": "object",
            "properties": {
                "images": {
                    "type": "array",
                    "description": "List of image dictionaries to analyze"
                },
                "article_context": {
                    "type": "string",
                    "description": "Article text for context"
                },
                "base_url": {
                    "type": "string",
                    "description": "Base URL of the article"
                },
                "max_size_mb": {
                    "type": "integer",
                    "description": "Maximum image size in MB",
                    "default": 3
                },
                "model_id": {
                    "type": "string",
                    "description": "Vision model ID to use",
                    "default": "anthropic.claude-3-haiku-20240307-v1:0"
                },
                "max_tokens": {
                    "type": "integer",
                    "description": "Maximum tokens for response",
                    "default": 300
                },
                "temperature": {
                    "type": "number",
                    "description": "Temperature for response generation",
                    "default": 0.1
                }
            },
            "required": ["images", "article_context", "base_url"]
        }