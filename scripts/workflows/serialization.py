#!/usr/bin/env python3
"""
Workflow serialization format.

Handles saving and loading workflows as JSON files compatible with
ComfyUI-style node-based workflows.
"""
import json
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple

from nodes.base import Node
from nodes.registry import get_registry
from engine.data import NodeConnection


class WorkflowSerializer:
    """Handles workflow serialization and deserialization"""
    
    def __init__(self):
        self.registry = get_registry()
    
    def serialize_workflow(self, nodes: Dict[str, Node], 
                         connections: List[NodeConnection],
                         metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Serialize a workflow to dictionary format.
        
        Args:
            nodes: Dictionary of nodes
            connections: List of connections between nodes
            metadata: Optional workflow metadata
            
        Returns:
            Dictionary representation of workflow
        """
        workflow = {
            "version": "1.0",
            "metadata": metadata or {},
            "nodes": [],
            "connections": []
        }
        
        # Serialize nodes
        for node_id, node in nodes.items():
            node_dict = {
                "id": node_id,
                "type": node.get_node_type(),
                "position": node.config.get("position", {"x": 0, "y": 0}),
                "inputs": {},
                "outputs": {}
            }
            
            # Serialize inputs (only non-connected ones)
            for input_name, port in node.inputs.items():
                # Check if this input is connected
                is_connected = any(
                    conn.to_node == node_id and conn.to_input == input_name
                    for conn in connections
                )
                
                if not is_connected:
                    value = node.config.get(input_name)
                    if value is not None or port.default is not None:
                        node_dict["inputs"][input_name] = value if value is not None else port.default
            
            workflow["nodes"].append(node_dict)
        
        # Serialize connections
        for conn in connections:
            workflow["connections"].append({
                "from": {
                    "node": conn.from_node,
                    "output": conn.from_output
                },
                "to": {
                    "node": conn.to_node,
                    "input": conn.to_input
                }
            })
        
        return workflow
    
    def deserialize_workflow(self, workflow_data: Dict[str, Any]) -> Tuple[Dict[str, Node], List[NodeConnection]]:
        """
        Deserialize a workflow from dictionary format.
        
        Args:
            workflow_data: Dictionary representation of workflow
            
        Returns:
            Tuple of (nodes_dict, connections_list)
        """
        nodes: Dict[str, Node] = {}
        connections: List[NodeConnection] = []
        
        # Deserialize nodes
        for node_data in workflow_data.get("nodes", []):
            node_id = node_data["id"]
            node_type = node_data["type"]
            
            # Get node config (inputs + position)
            config = node_data.get("inputs", {}).copy()
            config["position"] = node_data.get("position", {"x": 0, "y": 0})
            
            # Create node instance
            node = self.registry.create_node(node_type, node_id, **config)
            if node:
                nodes[node_id] = node
        
        # Deserialize connections
        for conn_data in workflow_data.get("connections", []):
            from_data = conn_data["from"]
            to_data = conn_data["to"]
            
            connection = NodeConnection(
                from_node=from_data["node"],
                from_output=from_data["output"],
                to_node=to_data["node"],
                to_input=to_data["input"]
            )
            connections.append(connection)
        
        return nodes, connections
    
    def save_workflow(self, workflow_path: Path, nodes: Dict[str, Node],
                     connections: List[NodeConnection],
                     metadata: Optional[Dict[str, Any]] = None):
        """
        Save workflow to JSON file.
        
        Args:
            workflow_path: Path to save workflow file
            nodes: Dictionary of nodes
            connections: List of connections
            metadata: Optional workflow metadata
        """
        workflow_data = self.serialize_workflow(nodes, connections, metadata)
        
        with open(workflow_path, 'w') as f:
            json.dump(workflow_data, f, indent=2, default=str)
    
    def load_workflow(self, workflow_path: Path) -> Tuple[Dict[str, Node], List[NodeConnection], Dict[str, Any]]:
        """
        Load workflow from JSON file.
        
        Args:
            workflow_path: Path to workflow file
            
        Returns:
            Tuple of (nodes_dict, connections_list, metadata)
        """
        with open(workflow_path, 'r') as f:
            workflow_data = json.load(f)
        
        nodes, connections = self.deserialize_workflow(workflow_data)
        metadata = workflow_data.get("metadata", {})
        
        return nodes, connections, metadata

