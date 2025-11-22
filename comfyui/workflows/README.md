# ComfyUI Workflow Templates

These workflow templates demonstrate different use cases for sync-toolkit nodes.

## Connected Workflow System

All nodes are now designed to connect together in a complete workflow:

1. **Start with Credentials** - Set up your credentials first
2. **Load Inputs** - Use `LoadVideo` and `LoadAudio` nodes to load your media files
3. **Configure Settings** - Use `VideoSettings` to set codec, fps, resolution, audio bit depth
4. **Process** - Connect video/audio data through processing nodes:
   - `DetectScenes` - Auto-detect scene boundaries
   - `ChunkVideo` - Split based on CSV cuts file
   - `CreateShots` - Create shots from CSV spotting data
5. **Rename** - Use `RenameFiles` to rename processed files sequentially
6. **Bounce** - Use `BounceVideo` to create final versions
7. **Upload** - Use `UploadToStorage` to upload to S3 or Supabase

### Data Types

Nodes pass structured data between each other:
- **VIDEO_DATA** - Contains video file paths and metadata
- **AUDIO_DATA** - Contains audio file paths and metadata  
- **DIRECTORY_DATA** - Contains directory path and file list
- **VIDEO_SETTINGS** - Contains encoding settings (codec, fps, resolution, etc.)
- **CREDENTIALS** - Contains authentication credentials

### Example Workflow Chain

```
Credentials → LoadVideo → DetectScenes → RenameFiles → BounceVideo → UploadToStorage
                ↓
            LoadAudio ────┘
```

## How to Use

1. **Load in ComfyUI:**
   - Open ComfyUI
   - Go to "Load" → "Load Workflow"
   - Select one of these JSON files
   - Update paths and settings as needed

2. **Update Paths:**
   - Replace `/path/to/...` with your actual file paths
   - Update bucket names, S3 paths, etc.

3. **Connect Nodes:**
   - Connect outputs to inputs as shown in the connections section
   - Use the `credentials` input if you have a Credentials node
   - Connect `video_data` outputs to `video_data` inputs
   - Connect `directory_data` outputs to `directory_data` inputs

## Available Workflows

### 01_scene_detection.json
Basic scene detection workflow
- Detect scenes in video
- Extract audio from videos

### 02_full_pipeline.json
Complete end-to-end pipeline
- Detect scenes → Upload to S3 → Batch process → Download results
- Shows how to chain nodes together

### 03_csv_processing.json
CSV and URL list processing
- Process CSV files with S3 URLs
- Process URL lists directly
- Two examples - use one or the other

### 04_video_processing.json
Video processing workflows
- Create shots from CSV
- Group clips by faces
- Bounce videos
- Chunk videos from cuts file

### 05_storage_workflow.json
Storage operations
- Upload to S3
- Upload to Supabase
- Monitor S3 uploads
- Download from S3

### 06_utility_workflow.json
Utility operations
- Convert single timecode
- Convert CSV timecodes
- Rename files sequentially

## Auto-Update

Since the nodes are installed via symlink, **changes are automatically reflected** in ComfyUI:
- No need to reinstall after code changes
- Just restart ComfyUI or reload nodes
- The symlink points directly to your development directory

## Testing

1. **Start ComfyUI:**
   ```bash
   cd ~/Documents/ComfyUI
   python main.py
   ```

2. **Load a workflow** from the `workflows/` directory

3. **Update paths** to match your files

4. **Run the workflow** and check outputs

5. **Check node outputs** - each node returns useful data:
   - `output_directory` - where files were created
   - `manifest_path` - manifest file location
   - `count` values - number of items processed
   - Error messages if something fails

