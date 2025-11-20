# Node-Based Workflow System

A ComfyUI-style node-based workflow system for Sync Toolkit, allowing visual workflow design and execution.

> **Note**: This is a standalone system inspired by ComfyUI's design patterns. It is NOT integrated with ComfyUI itself. See [COMFYUI_INTEGRATION.md](COMFYUI_INTEGRATION.md) for details on potential integration options.

## Overview

The node-based workflow system transforms the CLI-based sync-toolkit into a visual, composable workflow system where:

- **Nodes** represent operations (video processing, storage, API calls)
- **Connections** define data flow between nodes
- **Workflows** can be saved, shared, and reused as JSON files
- **Execution** is automatic with dependency resolution and parallel processing

## Quick Start

### List Available Nodes

```bash
python scripts/sync_toolkit.py workflow list-nodes
```

### Execute a Workflow

```bash
python scripts/sync_toolkit.py workflow execute workflows/examples/simple_scene_detection.json
```

### Validate a Workflow

```bash
python scripts/sync_toolkit.py workflow validate workflows/examples/simple_scene_detection.json
```

## Node Types

### Input Nodes

- **LoadVideoNode** - Load video file(s) from local path
- **LoadAudioNode** - Load audio file(s) from local path
- **LoadCSVNode** - Load CSV file
- **LoadManifestNode** - Load manifest file (uploaded_urls.txt format)
- **LoadDirectoryNode** - Load directory of files

### Video Processing Nodes

- **DetectScenesNode** - Detect scene boundaries in video
- **CreateShotsNode** - Create video shots from CSV spotting data
- **GroupByFaceNode** - Group video clips by detected faces
- **ExtractAudioNode** - Extract audio from videos
- **BounceVideoNode** - Create bounced versions of videos

### Storage Nodes

- **UploadSupabaseNode** - Upload files to Supabase Storage
- **UploadS3Node** - Upload files to AWS S3
- **DownloadS3Node** - Download files from AWS S3

### API Processing Nodes

- **BatchLipsyncNode** - Batch lipsync processing from manifest file
- **ProcessCSVNode** - Process CSV file with S3 URLs

### Utility Nodes

- **ConvertTimecodesNode** - Convert timecodes between frame rates
- **MonitorS3Node** - Monitor S3 upload progress
- **CreateManifestNode** - Create manifest file from video/audio lists
- **MergeResultsNode** - Merge multiple result JSONs

## Workflow Format

Workflows are stored as JSON files with the following structure:

```json
{
  "version": "1.0",
  "metadata": {
    "name": "Workflow Name",
    "description": "Workflow description"
  },
  "nodes": [
    {
      "id": "node_1",
      "type": "LoadVideoNode",
      "position": {"x": 100, "y": 100},
      "inputs": {
        "video_path": "/path/to/video.mov"
      }
    }
  ],
  "connections": [
    {
      "from": {"node": "node_1", "output": "video_path"},
      "to": {"node": "node_2", "input": "video_path"}
    }
  ]
}
```

### Node Definition

Each node has:
- **id**: Unique identifier within the workflow
- **type**: Node type name (e.g., "LoadVideoNode")
- **position**: Visual position for UI (x, y coordinates)
- **inputs**: Input values (either direct values or connected from other nodes)

### Connection Definition

Connections link node outputs to node inputs:
- **from**: Source node ID and output name
- **to**: Destination node ID and input name

## Example Workflows

### Simple Scene Detection

```json
{
  "version": "1.0",
  "nodes": [
    {
      "id": "load_video",
      "type": "LoadVideoNode",
      "position": {"x": 100, "y": 100},
      "inputs": {"video_path": "/path/to/video.mov"}
    },
    {
      "id": "detect_scenes",
      "type": "DetectScenesNode",
      "position": {"x": 300, "y": 100},
      "inputs": {"threshold": 22.0}
    }
  ],
  "connections": [
    {
      "from": {"node": "load_video", "output": "video_path"},
      "to": {"node": "detect_scenes", "input": "video_path"}
    }
  ]
}
```

### CSV-Based Processing

```json
{
  "version": "1.0",
  "nodes": [
    {
      "id": "load_csv",
      "type": "LoadCSVNode",
      "position": {"x": 100, "y": 100},
      "inputs": {"csv_path": "/path/to/input.csv"}
    },
    {
      "id": "process_csv",
      "type": "ProcessCSVNode",
      "position": {"x": 300, "y": 100},
      "inputs": {"test_mode": false}
    }
  ],
  "connections": [
    {
      "from": {"node": "load_csv", "output": "csv_path"},
      "to": {"node": "process_csv", "input": "csv_path"}
    }
  ]
}
```

## Execution Model

### Dependency Resolution

The execution engine:
1. Builds a dependency graph from node connections
2. Topologically sorts nodes for execution order
3. Groups nodes by execution level (parallel execution within levels)

### Parallel Execution

Nodes at the same execution level run in parallel (up to `--max-workers` limit).

### Result Caching

Node results are cached by input hash, allowing incremental re-execution of workflows.

### Error Handling

Failed nodes propagate errors to dependent nodes. The workflow continues executing independent branches.

## Architecture

### Core Components

- **nodes/base.py** - Base Node class and port system
- **nodes/registry.py** - Node type registry and discovery
- **engine/executor.py** - Workflow execution engine
- **engine/data.py** - Data flow management
- **workflows/serialization.py** - Workflow save/load

### Node Implementation

Nodes wrap existing CLI scripts, maintaining backward compatibility:

```python
@register_node(metadata={"category": "video"})
class DetectScenesNode(Node):
    def _define_ports(self):
        # Define inputs and outputs
        pass
    
    def execute(self, inputs):
        # Call underlying script or function
        return outputs
```

## Benefits

1. **Visual Workflow Design** - See entire pipeline at a glance
2. **Reusability** - Save and reuse common workflows
3. **Parallelization** - Automatic parallel execution
4. **Error Isolation** - Easier to debug failed nodes
5. **Experimentation** - Quickly test different configurations
6. **Documentation** - Workflows serve as visual documentation
7. **Collaboration** - Share workflows as JSON files
8. **Extensibility** - Easy to add new node types

## Future Enhancements

- Web-based visual editor (ComfyUI-style)
- Workflow templates library
- Node search and filtering
- Batch workflow execution
- Workflow scheduling
- Real-time execution monitoring
- Node result preview/visualization

## Backward Compatibility

The node system maintains full backward compatibility with existing CLI scripts. Nodes call underlying scripts, so all existing functionality remains available.

