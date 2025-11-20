# Example Workflows

This directory contains example workflows demonstrating the node-based workflow system.

## Available Examples

### simple_scene_detection.json

A basic workflow that:
1. Loads a video file
2. Detects scene boundaries
3. Uploads scenes to S3

**Usage**:
```bash
# Edit the workflow file to set your video path and S3 destination
python scripts/sync_toolkit.py workflow execute workflows/examples/simple_scene_detection.json
```

### complex_pipeline.json

A complete lipsync processing pipeline that:
1. Loads video and audio files
2. Extracts audio from video
3. Uploads to S3
4. Creates manifest file
5. Runs batch lipsync processing
6. Downloads results
7. Bounces final videos

**Usage**:
```bash
# Edit the workflow file to set your paths and S3 destinations
python scripts/sync_toolkit.py workflow execute workflows/examples/complex_pipeline.json
```

## Customizing Workflows

To use these examples:

1. **Copy the workflow file**:
   ```bash
   cp workflows/examples/simple_scene_detection.json my_workflow.json
   ```

2. **Edit the workflow** to set your paths:
   - Update `video_path`, `audio_path`, `csv_path`, etc. in node inputs
   - Update S3 destinations (`s3://bucket/path/`)
   - Adjust node parameters (thresholds, frame rates, etc.)

3. **Validate the workflow**:
   ```bash
   python scripts/sync_toolkit.py workflow validate my_workflow.json
   ```

4. **Execute the workflow**:
   ```bash
   python scripts/sync_toolkit.py workflow execute my_workflow.json
   ```

## Creating New Workflows

1. **List available nodes**:
   ```bash
   python scripts/sync_toolkit.py workflow list-nodes
   ```

2. **Create workflow JSON** following the format:
   ```json
   {
     "version": "1.0",
     "nodes": [...],
     "connections": [...]
   }
   ```

3. **Validate and execute** as shown above.

## Tips

- Start with simple workflows and add complexity gradually
- Use the `validate` command to check workflows before execution
- Set `--max-workers` appropriately for your system
- Use `--no-cache` to force re-execution of all nodes
- Check execution results with `--output` flag

