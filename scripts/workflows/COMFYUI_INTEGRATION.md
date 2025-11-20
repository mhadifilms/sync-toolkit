# ComfyUI Integration Guide

## Current Status

**This is NOT currently integrated with ComfyUI.** It's a standalone node-based workflow system that uses similar design patterns to ComfyUI but operates independently.

## What This System Is

- **Standalone CLI-based system** - Runs via command line, no web UI
- **Video processing focused** - Designed for lipsync/video workflows, not AI image generation
- **JSON workflow format** - Similar structure to ComfyUI but not directly compatible
- **Python-based execution** - Runs workflows programmatically

## What ComfyUI Is

- **Web-based visual editor** - Drag-and-drop node interface in browser
- **AI image generation focused** - Primarily for Stable Diffusion workflows
- **Custom node ecosystem** - Extensible via custom node packs
- **Real-time execution** - Visual feedback during workflow execution

## Could This Work With ComfyUI?

Yes, but it would require creating **ComfyUI custom nodes**. Here's how:

### Option 1: Create ComfyUI Custom Node Pack

You could create a custom node pack that wraps sync-toolkit operations:

```python
# Example ComfyUI custom node structure
class SyncToolkitDetectScenes:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "video_path": ("STRING", {"default": ""}),
                "threshold": ("FLOAT", {"default": 22.0, "min": 0, "max": 100})
            }
        }
    
    RETURN_TYPES = ("STRING", "STRING")  # output_dir, scene_list
    FUNCTION = "execute"
    CATEGORY = "sync-toolkit"
    
    def execute(self, video_path, threshold):
        # Call sync-toolkit node system
        from nodes.video_nodes import DetectScenesNode
        node = DetectScenesNode("temp", video_path=video_path, threshold=threshold)
        result = node.execute({"video_path": video_path, "threshold": threshold})
        return result["output_directory"], str(result["scene_list"])
```

### Option 2: Web UI Integration

Build a web-based visual editor similar to ComfyUI that uses this node system:

- Use React Flow or similar for the canvas
- Connect to the Python execution engine via API
- Display nodes visually with drag-and-drop
- Show real-time execution progress

### Option 3: Workflow Format Converter

Create a converter between ComfyUI workflow format and sync-toolkit format:

```python
def comfyui_to_synctoolkit(comfyui_workflow):
    """Convert ComfyUI workflow to sync-toolkit format"""
    # Map ComfyUI nodes to sync-toolkit nodes
    # Convert connection format
    # Return sync-toolkit workflow JSON
```

## Current Usage

Right now, you use this system **independently**:

```bash
# Execute workflows via CLI
python scripts/sync_toolkit.py workflow execute workflow.json
```

## Future: Web UI (ComfyUI-Style)

The architecture is designed to support a web UI. To build one:

1. **Backend API** - FastAPI/Flask server exposing:
   - Workflow execution endpoints
   - Node registry API
   - Real-time progress via WebSocket

2. **Frontend** - React/Vue.js application with:
   - Canvas for node placement (React Flow, Vue Flow)
   - Node property editors
   - Connection system
   - Execution visualization

3. **Integration** - Connect frontend to existing execution engine

## Comparison

| Feature | This System | ComfyUI |
|---------|-------------|---------|
| **UI** | CLI only | Web-based visual editor |
| **Focus** | Video processing | AI image generation |
| **Execution** | Python subprocess | Python execution engine |
| **Workflow Format** | Custom JSON | Custom JSON (different structure) |
| **Extensibility** | Node registry | Custom node packs |
| **Real-time Updates** | No | Yes (WebSocket) |

## Recommendation

**For now**: Use this system standalone via CLI for video processing workflows.

**Future**: If you want ComfyUI integration:
1. Create custom node pack for ComfyUI (Option 1)
2. Build web UI using this system (Option 2)
3. Use both systems independently for different purposes

The node architecture makes it relatively straightforward to add a web UI later, but that's a separate project from the core execution engine.

