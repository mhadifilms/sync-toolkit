#!/usr/bin/env python3
"""
Node registry for managing available node types.

Automatically discovers and registers node classes.
"""
from typing import Dict, Type, Optional, List
import importlib
import inspect
from pathlib import Path

from .base import Node


class NodeRegistry:
    """Registry for all available node types"""
    
    def __init__(self):
        self._nodes: Dict[str, Type[Node]] = {}
        self._node_metadata: Dict[str, Dict] = {}
    
    def register(self, node_class: Type[Node], metadata: Optional[Dict] = None):
        """
        Register a node class.
        
        Args:
            node_class: Node class to register
            metadata: Optional metadata about the node
        """
        node_type = node_class.__name__
        self._nodes[node_type] = node_class
        self._node_metadata[node_type] = metadata or {}
    
    def get_node_class(self, node_type: str) -> Optional[Type[Node]]:
        """Get node class by type name"""
        return self._nodes.get(node_type)
    
    def create_node(self, node_type: str, node_id: str, **config) -> Optional[Node]:
        """
        Create a node instance.
        
        Args:
            node_type: Type name of the node
            node_id: Unique identifier for the node
            **config: Node configuration parameters
            
        Returns:
            Node instance or None if type not found
        """
        node_class = self.get_node_class(node_type)
        if node_class is None:
            return None
        
        try:
            return node_class(node_id=node_id, **config)
        except Exception as e:
            print(f"Error creating node {node_type}: {e}")
            return None
    
    def list_node_types(self) -> List[str]:
        """List all registered node types"""
        return list(self._nodes.keys())
    
    def get_node_metadata(self, node_type: str) -> Dict:
        """Get metadata for a node type"""
        return self._node_metadata.get(node_type, {})
    
    def discover_nodes(self, package_path: Path):
        """
        Automatically discover and register nodes from a package.
        
        Args:
            package_path: Path to package containing node modules
        """
        if not package_path.exists():
            return
        
        # Import all modules in the package
        for module_file in package_path.glob("*.py"):
            if module_file.name.startswith("_") or module_file.name == "base.py":
                continue
            
            module_name = f"nodes.{module_file.stem}"
            try:
                module = importlib.import_module(module_name)
                
                # Find all Node subclasses
                for name, obj in inspect.getmembers(module):
                    if (inspect.isclass(obj) and 
                        issubclass(obj, Node) and 
                        obj is not Node):
                        self.register(obj)
            except Exception as e:
                print(f"Error discovering nodes from {module_file}: {e}")


# Global registry instance
_registry = None


def get_registry() -> NodeRegistry:
    """Get the global node registry (lazy initialization)"""
    global _registry
    if _registry is None:
        _registry = NodeRegistry()
        # Auto-discover nodes from this package
        from pathlib import Path
        nodes_dir = Path(__file__).parent
        _registry.discover_nodes(nodes_dir)
    return _registry


def register_node(metadata: Optional[Dict] = None):
    """
    Decorator to register a node class.
    
    Usage:
        @register_node(metadata={"category": "video"})
        class MyNode(Node):
            ...
    """
    def decorator(node_class: Type[Node]):
        _registry.register(node_class, metadata)
        return node_class
    return decorator

