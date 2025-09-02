"""
Base tool class for the web scraping system using AWS Strands SDK patterns.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any
import json
from datetime import datetime


class BaseTool(ABC):
    """Base class for all tools in the scraping system"""
    
    def __init__(self, name: str, description: str):
        self.name = name
        self.description = description
        self.execution_count = 0
        self.last_execution = None
    
    @abstractmethod
    def execute(self, **kwargs) -> Dict[str, Any]:
        """Execute the tool with given parameters"""
        pass
    
    def _log_execution(self):
        """Log tool execution for debugging"""
        self.execution_count += 1
        self.last_execution = datetime.utcnow().isoformat() + "Z"
    
    def get_metadata(self) -> Dict[str, Any]:
        """Get tool metadata"""
        return {
            "name": self.name,
            "description": self.description,
            "execution_count": self.execution_count,
            "last_execution": self.last_execution
        }
    
    def to_strands_tool_spec(self) -> Dict[str, Any]:
        """Convert to Strands SDK tool specification format"""
        return {
            "name": self.name,
            "description": self.description,
            "input_schema": self._get_input_schema(),
            "function": self.execute
        }
    
    @abstractmethod
    def _get_input_schema(self) -> Dict[str, Any]:
        """Define the input schema for this tool"""
        pass