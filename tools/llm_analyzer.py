"""
LLM Analyzer tool for generic LLM-based content analysis.
"""

import os
import json
import boto3
from typing import Dict, Any, List
from dotenv import load_dotenv

from .base_tool import BaseTool

load_dotenv()


class LLMAnalyzer(BaseTool):
    """Tool for generic LLM-based content analysis"""
    
    def __init__(self):
        super().__init__(
            name="LLMAnalyzer",
            description="Generic tool for LLM-based content analysis and processing"
        )
        self.bedrock_client = boto3.client(
            'bedrock-runtime',
            aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
            aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'),
            region_name=os.getenv('AWS_REGION', 'us-east-1')
        )
        self.default_model = "anthropic.claude-3-haiku-20240307-v1:0"
    
    def execute(self, task_type: str, content: str, prompt_template: str, **kwargs) -> Dict[str, Any]:
        """
        Execute LLM analysis task
        
        Args:
            task_type: Type of analysis ('content_validation', 'structure_analysis', 'text_scoring', etc.)
            content: Content to analyze
            prompt_template: Template for the LLM prompt
            **kwargs: Additional parameters for the analysis
            
        Returns:
            Dict containing analysis results
        """
        self._log_execution()
        
        try:
            # Format the prompt
            prompt = prompt_template.format(content=content, **kwargs)
            
            # Prepare the request
            max_tokens = kwargs.get('max_tokens', 200)
            temperature = kwargs.get('temperature', 0.1)
            model_id = kwargs.get('model_id', self.default_model)
            
            body = json.dumps({
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": max_tokens,
                "temperature": temperature,
                "messages": [{"role": "user", "content": prompt}]
            })
            
            # Make the API call
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
                "task_type": task_type,
                "raw_response": result,
                "parsed_result": self._parse_response(task_type, result, **kwargs),
                "analysis_metadata": {
                    "model_used": model_id,
                    "prompt_length": len(prompt),
                    "response_length": len(result),
                    "tokens_used": max_tokens
                }
            }
            
        except Exception as e:
            return {
                "success": False,
                "task_type": task_type,
                "error": str(e),
                "parsed_result": None
            }
    
    def _parse_response(self, task_type: str, response: str, **kwargs) -> Dict[str, Any]:
        """Parse LLM response based on task type"""
        
        if task_type == "content_validation":
            return self._parse_content_validation(response, kwargs.get('total_chunks', 0))
        elif task_type == "structure_analysis":
            return {"guidance": response}
        elif task_type == "text_scoring":
            return self._parse_text_scoring(response)
        else:
            return {"raw_response": response}
    
    def _parse_content_validation(self, response: str, total_chunks: int) -> Dict[str, Any]:
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
                            idx = int(chunk_num) - 1  # Convert to 0-based index
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
    
    def _parse_text_scoring(self, response: str) -> Dict[str, Any]:
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
    
    # Predefined prompt templates for common tasks
    @staticmethod
    def get_content_validation_prompt() -> str:
        """Get template for content validation task"""
        return """Analyze this extracted web content for coherence and relevance. Apply balanced filtering - keep main content, remove obvious noise.

URL: {url}

CONTENT TO VALIDATE:
{content}

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
    
    @staticmethod
    def get_structure_analysis_prompt() -> str:
        """Get template for page structure analysis"""
        return """Analyze this HTML structure and identify the main content areas that contain valuable information.
Focus on:
- Primary article/content body
- Main headings and text sections
- Relevant images and figures
- Avoid navigation, ads, sidebars, footers

HTML sample:
{content}

Provide guidance on what content to prioritize for extraction."""
    
    @staticmethod
    def get_text_scoring_prompt() -> str:
        """Get template for text relevance scoring"""
        return """Rate the relevance of this text content (1-10) based on whether it represents main valuable information:

Guidance: {guidance}

Text: {content}

Respond with just: SCORE|REASON
Example: 8|Contains main article content with key information"""
    
    def _get_input_schema(self) -> Dict[str, Any]:
        """Define input schema for Strands SDK"""
        return {
            "type": "object",
            "properties": {
                "task_type": {
                    "type": "string",
                    "description": "Type of analysis task to perform"
                },
                "content": {
                    "type": "string",
                    "description": "Content to analyze"
                },
                "prompt_template": {
                    "type": "string",
                    "description": "Template for the LLM prompt"
                },
                "max_tokens": {
                    "type": "integer",
                    "description": "Maximum tokens for response",
                    "default": 200
                },
                "temperature": {
                    "type": "number",
                    "description": "Temperature for LLM response",
                    "default": 0.1
                },
                "model_id": {
                    "type": "string",
                    "description": "Model ID to use for analysis",
                    "default": "anthropic.claude-3-haiku-20240307-v1:0"
                }
            },
            "required": ["task_type", "content", "prompt_template"]
        }