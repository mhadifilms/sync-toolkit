# Web UI for Sync Toolkit Workflows

A ComfyUI-style visual editor for creating and executing node-based workflows.

## Quick Start

```bash
# Install dependencies
pip install -r scripts/web/requirements.txt

# Start the web server
python scripts/sync_toolkit.py workflow ui

# Open http://127.0.0.1:8000 in your browser
```

## Features

- **Drag-and-Drop Node Creation** - Browse available nodes in the sidebar and drag them onto the canvas
- **Visual Connections** - Connect nodes by clicking and dragging from output ports to input ports
- **Node Configuration** - Edit node properties directly in the node interface
- **Workflow Execution** - Execute workflows with real-time status updates
- **Save/Load** - Save workflows as JSON files and load them back
- **Validation** - Validate workflows before execution

## Usage

### Creating a Workflow

1. **Add Nodes**: Drag nodes from the sidebar onto the canvas
2. **Configure Nodes**: Click on nodes to select them, then edit their properties
3. **Connect Nodes**: Click on an output port (right side) and drag to an input port (left side)
4. **Execute**: Click the "Execute" button to run the workflow

### Saving Workflows

Click "Save" and enter a file path (e.g., `workflows/my_workflow.json`). The workflow will be saved in JSON format.

### Loading Workflows

Click "Load" and enter the path to a saved workflow file. The workflow will be loaded onto the canvas.

## API Endpoints

The web server provides REST API endpoints:

- `GET /api/nodes` - List all available node types
- `POST /api/workflow/validate` - Validate a workflow
- `POST /api/workflow/execute` - Execute a workflow
- `POST /api/workflow/save` - Save a workflow to file
- `GET /api/workflow/load` - Load a workflow from file
- `WebSocket /ws` - Real-time execution updates (future)

## Development

The web UI consists of:

- **Backend** (`server.py`) - FastAPI server with REST API and WebSocket support
- **Frontend** (`static/index.html`) - Single-page HTML/JavaScript application

### Adding Features

To add new features to the web UI:

1. **Backend**: Add new endpoints in `server.py`
2. **Frontend**: Update `static/index.html` with new UI elements and JavaScript

### Styling

The UI uses inline CSS for simplicity. For production, consider:
- Extracting CSS to separate files
- Using a CSS framework (Tailwind, Bootstrap)
- Adding a build process (Webpack, Vite)

## Troubleshooting

### Port Already in Use

If port 8000 is already in use:
```bash
python scripts/sync_toolkit.py workflow ui --port 8001
```

### CORS Issues

If accessing from a different host:
```bash
python scripts/sync_toolkit.py workflow ui --host 0.0.0.0
```

### Missing Dependencies

Make sure all dependencies are installed:
```bash
pip install -r scripts/web/requirements.txt
```

## Future Enhancements

- [ ] Real-time execution progress via WebSocket
- [ ] Node result preview/visualization
- [ ] Workflow templates library
- [ ] Undo/redo functionality
- [ ] Zoom and pan for large workflows
- [ ] Node search and filtering
- [ ] Keyboard shortcuts
- [ ] Multi-select and bulk operations

