"""
Decorators for the web scraping system to mark tools and agents.
"""

from typing import Dict, Any, Callable, Optional
from functools import wraps
import inspect


def tool(name: Optional[str] = None, description: Optional[str] = None):
    """
    Decorator to mark a class as a tool and automatically register it.
    
    Usage:
        @tool(name="HTMLFetcher", description="Fetches HTML content")
        class HTMLFetcher:
            def execute(self, **kwargs):
                pass
    """
    def decorator(cls):
        # Set tool metadata
        cls._tool_name = name or cls.__name__
        cls._tool_description = description or cls.__doc__ or f"{cls.__name__} tool"
        cls._is_tool = True
        
        # Auto-register in tool registry
        ToolRegistry.register(cls._tool_name, cls)
        
        # Add Strands SDK compatibility method
        def to_strands_tool_spec(self) -> Dict[str, Any]:
            return {
                "name": self._tool_name,
                "description": self._tool_description,
                "input_schema": self._get_input_schema() if hasattr(self, '_get_input_schema') else {},
                "function": self.execute
            }
        
        cls.to_strands_tool_spec = to_strands_tool_spec
        
        return cls
    
    return decorator


def agent(name: Optional[str] = None, description: Optional[str] = None, tools: Optional[list] = None):
    """
    Decorator to mark a class as an agent and automatically configure it.
    
    Usage:
        @agent(name="WebScraper", description="Scrapes web content", tools=["HTMLFetcher", "TextExtractor"])
        class WebScraperAgent:
            def execute(self, **kwargs):
                pass
    """
    def decorator(cls):
        # Set agent metadata
        cls._agent_name = name or cls.__name__
        cls._agent_description = description or cls.__doc__ or f"{cls.__name__} agent"
        cls._agent_tools = tools or []
        cls._is_agent = True
        
        # Auto-register in agent registry
        AgentRegistry.register(cls._agent_name, cls)
        
        # Add tool auto-injection in __init__
        original_init = cls.__init__
        
        @wraps(original_init)
        def new_init(self, *args, **kwargs):
            # Initialize tools automatically
            self.tools = []
            for tool_name in cls._agent_tools:
                if isinstance(tool_name, str):
                    tool_class = ToolRegistry.get(tool_name)
                    if tool_class:
                        self.tools.append(tool_class())
                else:
                    self.tools.append(tool_name)
            
            # Call original init
            original_init(self, *args, **kwargs)
        
        cls.__init__ = new_init
        
        # Add Strands SDK compatibility method
        def to_strands_agent_spec(self) -> Dict[str, Any]:
            return {
                "name": self._agent_name,
                "description": self._agent_description,
                "tools": [tool.to_strands_tool_spec() if hasattr(tool, 'to_strands_tool_spec') else str(tool) for tool in self.tools],
                "execute": self.execute
            }
        
        cls.to_strands_agent_spec = to_strands_agent_spec
        
        return cls
    
    return decorator


def input_schema(**schema_fields):
    """
    Decorator to define input schema for tools.
    
    Usage:
        @input_schema(url={"type": "string", "required": True}, timeout={"type": "integer", "default": 10})
        def execute(self, **kwargs):
            pass
    """
    def decorator(func):
        func._input_schema = {
            "type": "object",
            "properties": schema_fields,
            "required": [field for field, spec in schema_fields.items() if spec.get("required", False)]
        }
        return func
    
    return decorator


class ToolRegistry:
    """Registry for managing tools"""
    _tools = {}
    
    @classmethod
    def register(cls, name: str, tool_class):
        cls._tools[name] = tool_class
    
    @classmethod
    def get(cls, name: str):
        return cls._tools.get(name)
    
    @classmethod
    def list_tools(cls) -> Dict[str, Any]:
        return {name: tool_class._tool_description for name, tool_class in cls._tools.items()}
    
    @classmethod
    def create_tool(cls, name: str, **kwargs):
        tool_class = cls.get(name)
        return tool_class(**kwargs) if tool_class else None


class AgentRegistry:
    """Registry for managing agents"""
    _agents = {}
    
    @classmethod
    def register(cls, name: str, agent_class):
        cls._agents[name] = agent_class
    
    @classmethod
    def get(cls, name: str):
        return cls._agents.get(name)
    
    @classmethod
    def list_agents(cls) -> Dict[str, Any]:
        return {name: agent_class._agent_description for name, agent_class in cls._agents.items()}
    
    @classmethod
    def create_agent(cls, name: str, **kwargs):
        agent_class = cls.get(name)
        return agent_class(**kwargs) if agent_class else None


def requires_tools(*tool_names):
    """
    Decorator to specify required tools for an agent method.
    
    Usage:
        @requires_tools("HTMLFetcher", "TextExtractor")
        def scrape(self, url):
            pass
    """
    def decorator(func):
        func._required_tools = tool_names
        
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            # Check if required tools are available
            available_tool_names = [getattr(tool, '_tool_name', str(tool)) for tool in self.tools]
            
            for required_tool in tool_names:
                if required_tool not in available_tool_names:
                    raise ValueError(f"Required tool '{required_tool}' not available. Available tools: {available_tool_names}")
            
            return func(self, *args, **kwargs)
        
        return wrapper
    
    return decorator