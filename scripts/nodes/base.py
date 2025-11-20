#!/usr/bin/env python3
"""
Base classes for node-based workflow system.

Defines the core Node class and port system for data flow.
"""
import hashlib
import json
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Union, Callable


class PortType(Enum):
    """Data types for node ports"""
    FILE = "file"  # Single file path
    DIRECTORY = "directory"  # Directory path
    FILE_LIST = "file_list"  # List of file paths
    URL_LIST = "url_list"  # List of URLs
    MANIFEST = "manifest"  # Manifest file structure
    CSV_DATA = "csv_data"  # CSV data structure
    JSON_DATA = "json_data"  # Generic JSON data
    VIDEO_METADATA = "video_metadata"  # Video properties
    SCENE_LIST = "scene_list"  # Scene detection results
    STRING = "string"  # Generic string
    INTEGER = "integer"  # Integer number
    FLOAT = "float"  # Floating point number
    BOOLEAN = "boolean"  # Boolean value


@dataclass
class InputPort:
    """Represents an input port on a node"""
    name: str
    port_type: PortType
    required: bool = True
    default: Any = None
    description: str = ""
    validator: Optional[Callable[[Any], bool]] = None
    
    def validate(self, value: Any) -> bool:
        """Validate input value"""
        if value is None:
            return not self.required or self.default is not None
        
        if self.validator:
            return self.validator(value)
        
        return True


@dataclass
class OutputPort:
    """Represents an output port on a node"""
    name: str
    port_type: PortType
    description: str = ""


class Node(ABC):
    """
    Base class for all workflow nodes.
    
    Each node represents a single operation in the workflow pipeline.
    Nodes have inputs and outputs that can be connected to other nodes.
    """
    
    def __init__(self, node_id: str, **kwargs):
        """
        Initialize a node.
        
        Args:
            node_id: Unique identifier for this node instance
            **kwargs: Node-specific configuration parameters
        """
        self.node_id = node_id
        self.config = kwargs
        self.inputs: Dict[str, InputPort] = {}
        self.outputs: Dict[str, OutputPort] = {}
        self._result_cache: Optional[Dict[str, Any]] = None
        self._execution_state: str = "pending"  # pending, running, completed, failed
        self._progress: float = 0.0  # 0.0 to 1.0
        self._error: Optional[str] = None
        
        # Define inputs and outputs
        self._define_ports()
    
    @abstractmethod
    def _define_ports(self):
        """Define input and output ports for this node type"""
        pass
    
    @abstractmethod
    def execute(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute the node's operation.
        
        Args:
            inputs: Dictionary of input values (already resolved from connected nodes)
            
        Returns:
            Dictionary of output values
        """
        pass
    
    def get_node_type(self) -> str:
        """Get the type name of this node"""
        return self.__class__.__name__
    
    def get_title(self) -> str:
        """Get display title for this node"""
        return self.__class__.__name__.replace("Node", "")
    
    def get_description(self) -> str:
        """Get description of what this node does"""
        return self.__doc__ or ""
    
    def validate(self) -> bool:
        """Validate node configuration"""
        # Check that all required inputs have values or defaults
        for name, port in self.inputs.items():
            if port.required and port.default is None:
                value = self.config.get(name)
                if value is None:
                    return False
                if not port.validate(value):
                    return False
        return True
    
    def get_input_hash(self) -> str:
        """Generate hash of input values for caching"""
        input_data = {}
        for name, port in self.inputs.items():
            value = self.config.get(name, port.default)
            input_data[name] = value
        
        # Also include node type and ID
        cache_key = {
            "node_type": self.get_node_type(),
            "node_id": self.node_id,
            "inputs": input_data
        }
        
        json_str = json.dumps(cache_key, sort_keys=True, default=str)
        return hashlib.sha256(json_str.encode()).hexdigest()
    
    def set_progress(self, progress: float):
        """Update execution progress (0.0 to 1.0)"""
        self._progress = max(0.0, min(1.0, progress))
    
    def get_progress(self) -> float:
        """Get current execution progress"""
        return self._progress
    
    def set_error(self, error: str):
        """Set error message"""
        self._error = error
        self._execution_state = "failed"
    
    def get_error(self) -> Optional[str]:
        """Get error message if execution failed"""
        return self._error
    
    def get_state(self) -> str:
        """Get current execution state"""
        return self._execution_state
    
    def set_state(self, state: str):
        """Set execution state"""
        self._execution_state = state
    
    def cache_result(self, result: Dict[str, Any]):
        """Cache execution result"""
        self._result_cache = result
        self._execution_state = "completed"
        self._progress = 1.0
    
    def get_cached_result(self) -> Optional[Dict[str, Any]]:
        """Get cached execution result"""
        return self._result_cache
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize node to dictionary"""
        return {
            "id": self.node_id,
            "type": self.get_node_type(),
            "config": self.config,
            "inputs": {name: {
                "type": port.port_type.value,
                "required": port.required,
                "default": port.default,
                "description": port.description
            } for name, port in self.inputs.items()},
            "outputs": {name: {
                "type": port.port_type.value,
                "description": port.description
            } for name, port in self.outputs.items()}
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Node":
        """Deserialize node from dictionary"""
        node_id = data["id"]
        config = data.get("config", {})
        return cls(node_id=node_id, **config)

