#!/usr/bin/env python3
"""
Web server for node-based workflow visual editor.

Provides REST API and WebSocket support for real-time workflow execution.
"""
import json
import asyncio
from pathlib import Path
from typing import Dict, List, Any, Optional
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
import uvicorn

from nodes.registry import get_registry
from engine.executor import WorkflowExecutor
from engine.data import NodeConnection
from workflows.serialization import WorkflowSerializer


app = FastAPI(title="Sync Toolkit Workflow Editor")

# Mount static files (HTML, CSS, JS)
static_dir = Path(__file__).parent / "static"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=static_dir), name="static")


class WorkflowRequest(BaseModel):
    nodes: List[Dict[str, Any]]
    connections: List[Dict[str, Any]]


class NodeCreateRequest(BaseModel):
    node_type: str
    node_id: str
    position: Dict[str, float]
    inputs: Dict[str, Any] = {}


@app.get("/")
async def index():
    """Serve the main editor page"""
    index_file = static_dir / "index.html"
    if index_file.exists():
        return FileResponse(index_file)
    return {"message": "Web UI not found. Please build the frontend."}


@app.get("/api/nodes")
async def list_nodes():
    """Get all available node types"""
    registry = get_registry()
    node_types = registry.list_node_types()
    
    nodes_info = []
    for node_type in node_types:
        metadata = registry.get_node_metadata(node_type)
        node_class = registry.get_node_class(node_type)
        
        # Create a temporary instance to get port info
        try:
            temp_node = registry.create_node(node_type, "temp")
            if temp_node:
                nodes_info.append({
                    "type": node_type,
                    "title": temp_node.get_title(),
                    "description": temp_node.get_description(),
                    "category": metadata.get("category", "other"),
                    "inputs": {
                        name: {
                            "type": port.port_type.value,
                            "required": port.required,
                            "default": port.default,
                            "description": port.description
                        }
                        for name, port in temp_node.inputs.items()
                    },
                    "outputs": {
                        name: {
                            "type": port.port_type.value,
                            "description": port.description
                        }
                        for name, port in temp_node.outputs.items()
                    }
                })
        except Exception as e:
            print(f"Error getting info for {node_type}: {e}")
    
    return {"nodes": nodes_info}


@app.post("/api/workflow/validate")
async def validate_workflow(request: WorkflowRequest):
    """Validate a workflow"""
    try:
        serializer = WorkflowSerializer()
        
        # Convert to workflow format
        workflow_data = {
            "version": "1.0",
            "nodes": request.nodes,
            "connections": request.connections
        }
        
        nodes, connections = serializer.deserialize_workflow(workflow_data)
        
        # Validate
        errors = []
        node_ids = set(nodes.keys())
        
        # Check nodes
        for node_id, node in nodes.items():
            if not node.validate():
                errors.append(f"Node {node_id}: Validation failed")
        
        # Check connections
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
        
        return {
            "valid": len(errors) == 0,
            "errors": errors
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/workflow/execute")
async def execute_workflow(request: WorkflowRequest):
    """Execute a workflow synchronously"""
    try:
        serializer = WorkflowSerializer()
        
        # Convert to workflow format
        workflow_data = {
            "version": "1.0",
            "nodes": request.nodes,
            "connections": request.connections
        }
        
        nodes, connections = serializer.deserialize_workflow(workflow_data)
        
        # Execute
        executor = WorkflowExecutor(max_workers=4, use_cache=True)
        result = executor.execute_workflow(nodes, connections)
        
        return {
            "success": result.success,
            "node_results": result.node_results,
            "errors": result.errors,
            "execution_time": result.execution_time,
            "total_nodes": result.total_nodes,
            "completed_nodes": result.completed_nodes,
            "failed_nodes": result.failed_nodes
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/workflow/save")
async def save_workflow(request: WorkflowRequest, path: str = Query(...)):
    """Save workflow to file"""
    try:
        workflow_data = {
            "version": "1.0",
            "nodes": request.nodes,
            "connections": request.connections
        }
        
        workflow_path = Path(path)
        workflow_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(workflow_path, 'w') as f:
            json.dump(workflow_data, f, indent=2, default=str)
        
        return {"success": True, "path": str(workflow_path)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/workflow/load")
async def load_workflow(path: str):
    """Load workflow from file"""
    try:
        serializer = WorkflowSerializer()
        workflow_path = Path(path)
        
        if not workflow_path.exists():
            raise HTTPException(status_code=404, detail="Workflow file not found")
        
        nodes, connections, metadata = serializer.load_workflow(workflow_path)
        
        # Convert back to API format
        workflow_data = serializer.serialize_workflow(nodes, connections, metadata)
        
        return workflow_data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# WebSocket for real-time execution updates
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
    
    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
    
    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)
    
    async def send_message(self, message: dict):
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except:
                pass


manager = ConnectionManager()


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time updates"""
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_json()
            
            if data.get("type") == "execute":
                # Execute workflow via WebSocket
                workflow_data = data.get("workflow", {})
                
                serializer = WorkflowSerializer()
                nodes, connections = serializer.deserialize_workflow(workflow_data)
                
                executor = WorkflowExecutor(max_workers=4, use_cache=True)
                
                # Send progress updates
                await manager.send_message({
                    "type": "execution_started",
                    "total_nodes": len(nodes)
                })
                
                # Execute (simplified - in real implementation, would need async execution)
                result = executor.execute_workflow(nodes, connections)
                
                await manager.send_message({
                    "type": "execution_complete",
                    "success": result.success,
                    "errors": result.errors,
                    "execution_time": result.execution_time
                })
            
    except WebSocketDisconnect:
        manager.disconnect(websocket)


def main():
    """Run the web server"""
    import argparse
    parser = argparse.ArgumentParser(description="Sync Toolkit Web UI")
    parser.add_argument("--host", default="127.0.0.1", help="Host to bind to")
    parser.add_argument("--port", type=int, default=8000, help="Port to bind to")
    parser.add_argument("--reload", action="store_true", help="Enable auto-reload")
    
    args = parser.parse_args()
    
    uvicorn.run(
        "web.server:app",
        host=args.host,
        port=args.port,
        reload=args.reload
    )


if __name__ == "__main__":
    main()

