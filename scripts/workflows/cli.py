#!/usr/bin/env python3
"""
CLI interface for node-based workflows.

Provides command-line interface for creating, executing, and managing workflows.
"""
import argparse
import json
import sys
from pathlib import Path
from typing import Dict, List

from nodes.base import Node
from nodes.registry import get_registry
from engine.executor import WorkflowExecutor
from engine.data import NodeConnection
from workflows.serialization import WorkflowSerializer


def list_nodes():
    """List all available node types"""
    registry = get_registry()
    node_types = registry.list_node_types()
    
    print("Available Node Types:")
    print("=" * 60)
    
    # Group by category
    categories = {}
    for node_type in node_types:
        metadata = registry.get_node_metadata(node_type)
        category = metadata.get("category", "other")
        if category not in categories:
            categories[category] = []
        categories[category].append((node_type, metadata))
    
    for category in sorted(categories.keys()):
        print(f"\n{category.upper()}:")
        for node_type, metadata in sorted(categories[category]):
            description = metadata.get("description", "")
            print(f"  {node_type:30} - {description}")


def create_workflow(args):
    """Create a new workflow interactively"""
    print("Workflow creation not yet implemented in CLI mode.")
    print("Use the workflow JSON format or web interface.")
    print("\nExample workflow format:")
    print(json.dumps({
        "version": "1.0",
        "nodes": [
            {
                "id": "node_1",
                "type": "LoadVideoNode",
                "position": {"x": 100, "y": 100},
                "inputs": {"video_path": "/path/to/video.mov"}
            }
        ],
        "connections": []
    }, indent=2))


def execute_workflow(args):
    """Execute a workflow from JSON file"""
    workflow_path = Path(args.workflow)
    
    if not workflow_path.exists():
        print(f"Error: Workflow file not found: {workflow_path}", file=sys.stderr)
        sys.exit(1)
    
    # Load workflow
    serializer = WorkflowSerializer()
    nodes, connections, metadata = serializer.load_workflow(workflow_path)
    
    if not nodes:
        print("Error: No nodes found in workflow", file=sys.stderr)
        sys.exit(1)
    
    print(f"Executing workflow: {workflow_path.name}")
    print(f"Nodes: {len(nodes)}, Connections: {len(connections)}")
    print("-" * 60)
    
    # Execute workflow
    executor = WorkflowExecutor(max_workers=args.max_workers, use_cache=args.cache)
    
    try:
        result = executor.execute_workflow(nodes, connections)
        
        print("\nExecution Results:")
        print("=" * 60)
        print(f"Success: {result.success}")
        print(f"Total Nodes: {result.total_nodes}")
        print(f"Completed: {result.completed_nodes}")
        print(f"Failed: {result.failed_nodes}")
        print(f"Execution Time: {result.execution_time:.2f}s")
        
        if result.errors:
            print("\nErrors:")
            for node_id, error in result.errors.items():
                print(f"  {node_id}: {error}")
        
        if args.output:
            # Save results
            output_path = Path(args.output)
            with open(output_path, 'w') as f:
                json.dump({
                    "success": result.success,
                    "node_results": result.node_results,
                    "errors": result.errors,
                    "execution_time": result.execution_time
                }, f, indent=2, default=str)
            print(f"\nResults saved to: {output_path}")
        
    finally:
        executor.cleanup()
    
    sys.exit(0 if result.success else 1)


def validate_workflow(args):
    """Validate a workflow file"""
    workflow_path = Path(args.workflow)
    
    if not workflow_path.exists():
        print(f"Error: Workflow file not found: {workflow_path}", file=sys.stderr)
        sys.exit(1)
    
    serializer = WorkflowSerializer()
    
    try:
        nodes, connections, metadata = serializer.load_workflow(workflow_path)
        
        print(f"Validating workflow: {workflow_path.name}")
        print("-" * 60)
        
        # Validate nodes
        errors = []
        for node_id, node in nodes.items():
            if not node.validate():
                errors.append(f"Node {node_id} ({node.get_node_type()}): Validation failed")
        
        # Validate connections
        node_ids = set(nodes.keys())
        for conn in connections:
            if conn.from_node not in node_ids:
                errors.append(f"Connection references unknown node: {conn.from_node}")
            if conn.to_node not in node_ids:
                errors.append(f"Connection references unknown node: {conn.to_node}")
            
            if conn.from_node in nodes:
                node = nodes[conn.from_node]
                if conn.from_output not in node.outputs:
                    errors.append(f"Node {conn.from_node} has no output: {conn.from_output}")
            
            if conn.to_node in nodes:
                node = nodes[conn.to_node]
                if conn.to_input not in node.inputs:
                    errors.append(f"Node {conn.to_node} has no input: {conn.to_input}")
        
        if errors:
            print("Validation Errors:")
            for error in errors:
                print(f"  - {error}")
            sys.exit(1)
        else:
            print("✓ Workflow is valid")
            print(f"  Nodes: {len(nodes)}")
            print(f"  Connections: {len(connections)}")
    
    except Exception as e:
        print(f"Error validating workflow: {e}", file=sys.stderr)
        sys.exit(1)


def main():
    """Main CLI entry point"""
    parser = argparse.ArgumentParser(
        description="Node-based workflow system for Sync Toolkit",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # List nodes command
    list_parser = subparsers.add_parser('list-nodes', help='List all available node types')
    
    # Create workflow command
    create_parser = subparsers.add_parser('create', help='Create a new workflow')
    
    # Execute workflow command
    execute_parser = subparsers.add_parser('execute', help='Execute a workflow')
    execute_parser.add_argument('workflow', help='Path to workflow JSON file')
    execute_parser.add_argument('--max-workers', type=int, default=4,
                                help='Maximum parallel node executions')
    execute_parser.add_argument('--no-cache', dest='cache', action='store_false',
                                help='Disable result caching')
    execute_parser.add_argument('--output', help='Save execution results to file')
    execute_parser.set_defaults(cache=True)
    
    # Validate workflow command
    validate_parser = subparsers.add_parser('validate', help='Validate a workflow file')
    validate_parser.add_argument('workflow', help='Path to workflow JSON file')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    if args.command == 'list-nodes':
        list_nodes()
    elif args.command == 'create':
        create_workflow(args)
    elif args.command == 'execute':
        execute_workflow(args)
    elif args.command == 'validate':
        validate_workflow(args)


if __name__ == '__main__':
    main()

