#!/usr/bin/env python3
"""
Data management for node-based workflows.

Handles data passing between nodes, serialization, and temporary file management.
"""
import json
import tempfile
import shutil
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
from dataclasses import dataclass

from nodes.base import Node, PortType


@dataclass
class NodeConnection:
    """Represents a connection between nodes"""
    from_node: str
    from_output: str
    to_node: str
    to_input: str


class DataManager:
    """Manages data flow between nodes"""
    
    def __init__(self, work_dir: Optional[Path] = None):
        """
        Initialize data manager.
        
        Args:
            work_dir: Working directory for temporary files (default: system temp)
        """
        if work_dir is None:
            work_dir = Path(tempfile.gettempdir()) / "sync-toolkit-workflows"
        
        self.work_dir = Path(work_dir)
        self.work_dir.mkdir(parents=True, exist_ok=True)
        
        self._node_results: Dict[str, Dict[str, Any]] = {}
        self._connections: List[NodeConnection] = []
    
    def add_connection(self, connection: NodeConnection):
        """Add a connection between nodes"""
        self._connections.append(connection)
    
    def set_node_result(self, node_id: str, outputs: Dict[str, Any]):
        """Store execution results for a node"""
        self._node_results[node_id] = outputs
    
    def get_node_result(self, node_id: str, output_name: str) -> Optional[Any]:
        """Get a specific output from a node's results"""
        if node_id not in self._node_results:
            return None
        return self._node_results[node_id].get(output_name)
    
    def resolve_node_inputs(self, node: Node, nodes: Dict[str, Node]) -> Dict[str, Any]:
        """
        Resolve all inputs for a node by following connections.
        
        Args:
            node: Node to resolve inputs for
            nodes: Dictionary of all nodes in the workflow
            
        Returns:
            Dictionary of resolved input values
        """
        resolved_inputs = {}
        
        # Start with node's own config values
        for input_name, port in node.inputs.items():
            if input_name in node.config:
                resolved_inputs[input_name] = node.config[input_name]
            elif port.default is not None:
                resolved_inputs[input_name] = port.default
        
        # Override with connected values
        for conn in self._connections:
            if conn.to_node == node.node_id and conn.to_input in node.inputs:
                # Get value from source node
                source_value = self.get_node_result(conn.from_node, conn.from_output)
                if source_value is not None:
                    resolved_inputs[conn.to_input] = source_value
        
        return resolved_inputs
    
    def cleanup(self):
        """Clean up temporary files"""
        if self.work_dir.exists():
            try:
                shutil.rmtree(self.work_dir)
            except Exception as e:
                print(f"Warning: Could not cleanup work directory: {e}")
    
    def create_temp_dir(self, prefix: str = "node") -> Path:
        """Create a temporary directory for node execution"""
        temp_dir = tempfile.mkdtemp(prefix=f"{prefix}_", dir=self.work_dir)
        return Path(temp_dir)
    
    def serialize_data(self, data: Any, port_type: PortType) -> Any:
        """
        Serialize data for storage/transmission.
        
        Args:
            data: Data to serialize
            port_type: Type of the data
            
        Returns:
            Serialized data
        """
        if port_type in [PortType.JSON_DATA, PortType.MANIFEST, PortType.CSV_DATA]:
            if isinstance(data, (dict, list)):
                return json.dumps(data)
            return data
        
        if port_type == PortType.FILE or port_type == PortType.DIRECTORY:
            if isinstance(data, Path):
                return str(data)
            return data
        
        if port_type == PortType.FILE_LIST or port_type == PortType.URL_LIST:
            return [str(item) if isinstance(item, Path) else item for item in data]
        
        return data
    
    def deserialize_data(self, data: Any, port_type: PortType) -> Any:
        """
        Deserialize data from storage/transmission.
        
        Args:
            data: Data to deserialize
            port_type: Type of the data
            
        Returns:
            Deserialized data
        """
        if port_type in [PortType.JSON_DATA, PortType.MANIFEST, PortType.CSV_DATA]:
            if isinstance(data, str):
                try:
                    return json.loads(data)
                except json.JSONDecodeError:
                    return data
            return data
        
        if port_type == PortType.FILE or port_type == PortType.DIRECTORY:
            if isinstance(data, str):
                return Path(data)
            return data
        
        if port_type == PortType.FILE_LIST:
            if isinstance(data, list):
                return [Path(item) if isinstance(item, str) else item for item in data]
            return data
        
        return data


def resolve_node_inputs(node: Node, nodes: Dict[str, Node], 
                       data_manager: DataManager) -> Dict[str, Any]:
    """
    Convenience function to resolve node inputs.
    
    Args:
        node: Node to resolve inputs for
        nodes: Dictionary of all nodes in the workflow
        data_manager: Data manager instance
        
    Returns:
        Dictionary of resolved input values
    """
    return data_manager.resolve_node_inputs(node, nodes)

