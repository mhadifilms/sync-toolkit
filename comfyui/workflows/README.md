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

All workflows are complete end-to-end pipelines that demonstrate the full capabilities of sync-toolkit.

### 00_episode.json ⭐ **MAIN WORKFLOW**
**Complete TV Episode to Lipsynced Outputs Pipeline** - End-to-end from raw episode to hundreds of lipsynced outputs

**Flow:**
1. **Credentials** - Set up AWS S3 and Sync.so API credentials
2. **LoadVideo** - Load raw TV episode video file
3. **LoadAudio** - Load raw TV episode audio file
4. **VideoSettings** - Configure encoding settings (codec, fps, resolution, audio bit depth)
5. **DetectScenes** - Automatically detect scene boundaries and split episode into hundreds of segments
6. **UploadToStorage** - Upload all scene segments to S3 and create manifest file (`uploaded_urls.txt`)
7. **LipsyncBatch** - Process all scenes through Sync.so API (reads manifest, processes all video/audio pairs)
8. **Output** - All lipsynced outputs saved to custom folder of choice

**Use Case:** Process a complete TV episode from raw video/audio files through scene detection, cloud upload, and batch lipsync processing to get hundreds of final outputs organized in your custom folder.

**Configuration Steps:**
1. **Credentials Node:**
   - Set `sync_api_key` - Your Sync.so API key
   - Set `aws_access_key_id` and `aws_secret_access_key` - AWS credentials for S3
   - Set `aws_region` - AWS region (e.g., "us-east-1")
   - Or use environment variables: `SYNC_API_KEY`, `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`

2. **LoadVideo Node:**
   - Set `video_path` to your TV episode video file (e.g., `/path/to/episode_001.mov`)

3. **LoadAudio Node:**
   - Set `audio_path` to your TV episode audio file (e.g., `/path/to/episode_001.wav`)

4. **VideoSettings Node:**
   - Configure output format (codec, fps, resolution, audio settings)
   - Default: ProRes 422, 23.976fps, 1920x1080, PCM 24-bit

5. **DetectScenes Node:**
   - Automatically detects scenes (no configuration needed)
   - Outputs hundreds of scene segments

6. **UploadToStorage Node:**
   - Set `s3_bucket` - Your S3 bucket name
   - Set `s3_dest` - S3 destination path (e.g., `s3://my-bucket/episodes/episode_001/scenes/`)
   - Creates `uploaded_urls.txt` manifest file automatically

7. **LipsyncBatch Node:**
   - Set `output_dir` - **Your custom output folder** (e.g., `/path/to/outputs/episode_001_lipsynced`)
   - Set `start_index` - Usually 1 (first scene)
   - Set `end_index` - **0 means process ALL scenes** (recommended)
   - Set `max_workers` - Parallel processing (1-15, default 15)
   - Set `check_exists` - Skip already processed files (recommended: true)
   - Set `keep_asd` - Force active speaker detection (optional)

**Output:**
- All lipsynced video files saved to your custom `output_dir` folder
- Each scene processed through Sync.so API with lipsync-2-pro model
- `batch_results.json` contains processing status for each scene
- Files named with scene indices (e.g., `scene_001.mp4`, `scene_002.mp4`, etc.)

**Processing Time:**
- Scene detection: ~5-15 minutes (depending on episode length)
- S3 upload: ~10-30 minutes (depending on number of scenes and bandwidth)
- Lipsync processing: ~2-5 minutes per scene (parallel processing with 15 workers)
- Total time for 100 scenes: ~3-8 hours (mostly API processing time)

---

### 01_grouping.json
**Scene Detection with Face Grouping Pipeline** - Detect scenes, group by faces, and upload

**Flow:**
1. **Credentials** - Set up AWS/Supabase credentials
2. **LoadVideo** - Load master video file
3. **LoadAudio** - Load master audio file
4. **DetectScenes** - Automatically detect scene boundaries and split video/audio
5. **GroupByFace** - Group scenes by detected faces and organize into folders
6. **RenameFiles** - Rename files sequentially
7. **BounceVideo** - Create final bounced versions
8. **UploadToStorage** - Upload to S3 with manifest generation

**Use Case:** Detect scenes, automatically group them by detected faces (useful for character-based organization), then upload to cloud storage.

**Configuration:**
- Update video/audio paths in LoadVideo and LoadAudio nodes
- Configure GroupByFace parameters (eps, min_samples) for face clustering sensitivity
- Set organize=true to create organized folder structure
- Set S3 bucket and destination path in UploadToStorage
- Add credentials in Credentials node

**Key Features:**
- Automatic face detection and clustering
- Organizes scenes by character/face groups
- Creates folder structure based on face groups
- All files properly renamed and bounced before upload

---

### 02_shots.json
**CSV Shots to Lipsync Pipeline** - Create shots from CSV, upload, and process through Sync API

**Flow:**
1. **Credentials** - Set up AWS S3 and Sync.so API credentials
2. **LoadVideo** - Load master video file
3. **CreateShots** - Create individual shots from CSV with Event Start/End times
4. **RenameFiles** - Rename shot files sequentially
5. **UploadToStorage** - Upload shots to S3 and create manifest
6. **ExtractAudio** - Extract audio from video shots (optional)
7. **LipsyncBatch** - Process all shots through Sync.so API

**Use Case:** Create individual video shots from a master video based on CSV spotting data, upload to S3, and process all shots through the Sync.so lipsync API.

**Configuration:**
- Update video path in LoadVideo node
- Set CSV path in CreateShots node (must have "Event Start Time" and "Event End Time" columns)
- Set S3 bucket and destination path in UploadToStorage
- Set output_dir in LipsyncBatch to your custom folder for final outputs
- Set end_index=0 in LipsyncBatch to process all shots
- Add credentials in Credentials node

**Key Features:**
- Complete pipeline from CSV to lipsynced outputs
- Automatic audio extraction if needed
- Batch processing through Sync API
- All outputs saved to custom folder

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
   - `output_directory` (DIRECTORY_DATA) - directory path, file count, and file list
   - `manifest_path` - manifest file location (for uploads)
   - `count` values - number of items processed
   - Error messages if something fails

## Quick Start

**All workflows are complete end-to-end pipelines. Start with `00_episode.json` for the most comprehensive solution.**

### Step-by-Step Setup:

1. **Load a workflow** (`00_episode.json`, `01_grouping.json`, or `02_shots.json`) in ComfyUI
2. **Configure Credentials:**
   - Add your Sync.so API key
   - Add your AWS credentials (or use environment variables)
3. **Set Input Files:**
   - Point `LoadVideo` to your TV episode video file
   - Point `LoadAudio` to your TV episode audio file
4. **Configure S3 Upload:**
   - Set your S3 bucket name
   - Set S3 destination path (e.g., `s3://my-bucket/episodes/episode_001/scenes/`)
5. **Set Output Directory:**
   - In `LipsyncBatch` node, set `output_dir` to your desired custom folder
   - Set `end_index` to `0` to process all scenes
6. **Run the workflow** - It will automatically:
   - Detect and split scenes
   - Upload to S3
   - Process through Sync API
   - Download all results to your custom folder

### Expected Output:

- **Hundreds of lipsynced video files** in your custom output folder
- Each file named with scene index (e.g., `scene_001.mp4`, `scene_002.mp4`)
- `batch_results.json` with processing status for each scene
- All files ready for further processing or delivery

---

## Workflow Customization

### Adding/Removing Steps

You can easily customize workflows by:
- **Adding nodes:** Insert additional processing nodes between existing ones
- **Removing nodes:** Delete nodes you don't need (e.g., skip BounceVideo if not needed)
- **Branching:** Split workflows to process the same data multiple ways

### Example: Skip Bounce Step

To skip the bounce step and upload directly:
1. Connect `RenameFiles` output directly to `UploadToStorage`
2. Remove the `BounceVideo` node

### Example: Process Multiple Outputs

After `DetectScenes`, you can:
- Connect to `RenameFiles` → `BounceVideo` → `UploadToStorage` (main path)
- Also connect to `ProcessCSV` for API processing (parallel path)

## Data Flow

The workflows demonstrate proper data flow:
- **VIDEO_DATA** flows from LoadVideo → processing nodes
- **AUDIO_DATA** flows from LoadAudio → processing nodes  
- **DIRECTORY_DATA** flows through: DetectScenes/CreateShots/ChunkVideo → RenameFiles → BounceVideo → UploadToStorage
- **CREDENTIALS** flows from Credentials → UploadToStorage (and other nodes that need auth)
- **VIDEO_SETTINGS** can be connected to nodes that support encoding settings (future enhancement)

