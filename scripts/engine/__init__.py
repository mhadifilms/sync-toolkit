"""
Execution engine for node-based workflows.

Handles workflow execution, dependency resolution, and parallel processing.
"""
from .executor import WorkflowExecutor, ExecutionResult
from .data import DataManager, resolve_node_inputs

__all__ = [
    'WorkflowExecutor',
    'ExecutionResult',
    'DataManager',
    'resolve_node_inputs',
]

