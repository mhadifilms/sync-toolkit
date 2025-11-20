#!/usr/bin/env python3
"""
Workflow execution engine.

Handles dependency resolution, parallel execution, and result caching.
"""
import time
from collections import defaultdict, deque
from dataclasses import dataclass
from typing import Dict, List, Optional, Set, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed

from nodes.base import Node
from nodes.registry import get_registry
from engine.data import DataManager, NodeConnection


@dataclass
class ExecutionResult:
    """Result of workflow execution"""
    success: bool
    node_results: Dict[str, Dict[str, any]]
    errors: Dict[str, str]
    execution_time: float
    total_nodes: int
    completed_nodes: int
    failed_nodes: int


class WorkflowExecutor:
    """Executes node-based workflows"""
    
    def __init__(self, max_workers: int = 4, use_cache: bool = True):
        """
        Initialize workflow executor.
        
        Args:
            max_workers: Maximum number of parallel node executions
            use_cache: Whether to use result caching
        """
        self.max_workers = max_workers
        self.use_cache = use_cache
        self.registry = get_registry()
        self.data_manager = DataManager()
        self._execution_log: List[Dict] = []
    
    def build_dependency_graph(self, nodes: Dict[str, Node], 
                              connections: List[NodeConnection]) -> Dict[str, List[str]]:
        """
        Build dependency graph from nodes and connections.
        
        Returns:
            Dictionary mapping node_id to list of dependent node_ids
        """
        dependencies: Dict[str, List[str]] = defaultdict(list)
        
        for conn in connections:
            # conn.to_node depends on conn.from_node
            if conn.to_node not in dependencies:
                dependencies[conn.to_node] = []
            dependencies[conn.to_node].append(conn.from_node)
        
        return dict(dependencies)
    
    def topological_sort(self, nodes: Dict[str, Node], 
                         dependencies: Dict[str, List[str]]) -> List[List[str]]:
        """
        Topologically sort nodes for execution.
        
        Returns:
            List of execution levels, where each level can be executed in parallel
        """
        # Calculate in-degree for each node
        in_degree: Dict[str, int] = {node_id: 0 for node_id in nodes}
        
        for node_id, deps in dependencies.items():
            for dep in deps:
                if dep in nodes:
                    in_degree[node_id] += 1
        
        # Find nodes with no dependencies (level 0)
        queue = deque([node_id for node_id, degree in in_degree.items() if degree == 0])
        levels: List[List[str]] = []
        
        while queue:
            level = []
            level_size = len(queue)
            
            for _ in range(level_size):
                node_id = queue.popleft()
                level.append(node_id)
                
                # Update in-degree for dependent nodes
                for dependent_id, deps in dependencies.items():
                    if node_id in deps:
                        in_degree[dependent_id] -= 1
                        if in_degree[dependent_id] == 0:
                            queue.append(dependent_id)
            
            if level:
                levels.append(level)
        
        return levels
    
    def execute_node(self, node: Node, nodes: Dict[str, Node]) -> Tuple[str, Dict[str, any], Optional[str]]:
        """
        Execute a single node.
        
        Returns:
            Tuple of (node_id, outputs_dict, error_message)
        """
        node_id = node.node_id
        
        try:
            # Check cache
            if self.use_cache:
                cached_result = node.get_cached_result()
                if cached_result is not None:
                    self.data_manager.set_node_result(node_id, cached_result)
                    return (node_id, cached_result, None)
            
            # Validate node
            if not node.validate():
                error = f"Node {node_id} validation failed"
                node.set_error(error)
                return (node_id, {}, error)
            
            # Resolve inputs
            inputs = self.data_manager.resolve_node_inputs(node, nodes)
            
            # Execute node
            node.set_state("running")
            node.set_progress(0.0)
            
            outputs = node.execute(inputs)
            
            # Cache result
            if self.use_cache:
                node.cache_result(outputs)
            
            # Store results
            self.data_manager.set_node_result(node_id, outputs)
            node.set_state("completed")
            node.set_progress(1.0)
            
            return (node_id, outputs, None)
            
        except Exception as e:
            error = f"Error executing node {node_id}: {str(e)}"
            node.set_error(error)
            node.set_state("failed")
            return (node_id, {}, error)
    
    def execute_workflow(self, nodes: Dict[str, Node], 
                        connections: List[NodeConnection]) -> ExecutionResult:
        """
        Execute a complete workflow.
        
        Args:
            nodes: Dictionary of nodes to execute
            connections: List of connections between nodes
            
        Returns:
            ExecutionResult with execution status and results
        """
        start_time = time.time()
        
        # Setup data manager
        self.data_manager = DataManager()
        for conn in connections:
            self.data_manager.add_connection(conn)
        
        # Build dependency graph
        dependencies = self.build_dependency_graph(nodes, connections)
        
        # Topological sort
        execution_levels = self.topological_sort(nodes, dependencies)
        
        # Track results
        node_results: Dict[str, Dict[str, any]] = {}
        errors: Dict[str, str] = {}
        completed = 0
        failed = 0
        
        # Execute levels sequentially, nodes within level in parallel
        for level in execution_levels:
            if not level:
                continue
            
            # Execute nodes in this level in parallel
            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                futures = {
                    executor.submit(self.execute_node, nodes[node_id], nodes): node_id
                    for node_id in level
                }
                
                for future in as_completed(futures):
                    node_id, outputs, error = future.result()
                    
                    if error:
                        errors[node_id] = error
                        failed += 1
                    else:
                        node_results[node_id] = outputs
                        completed += 1
                    
                    # Log execution
                    self._execution_log.append({
                        "node_id": node_id,
                        "success": error is None,
                        "error": error,
                        "timestamp": time.time()
                    })
        
        execution_time = time.time() - start_time
        
        return ExecutionResult(
            success=len(errors) == 0,
            node_results=node_results,
            errors=errors,
            execution_time=execution_time,
            total_nodes=len(nodes),
            completed_nodes=completed,
            failed_nodes=failed
        )
    
    def get_execution_log(self) -> List[Dict]:
        """Get execution log"""
        return self._execution_log
    
    def cleanup(self):
        """Clean up resources"""
        self.data_manager.cleanup()

