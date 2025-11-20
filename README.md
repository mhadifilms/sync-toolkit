# Sync Toolkit

A unified toolkit for bulk lipsync processing with Sync.so API. This toolkit provides a cohesive set of scripts that work together seamlessly, with interactive configuration and support for various input types.

## Features

- **Unified Configuration**: Interactive credential prompts - no environment variables needed
- **Modular Workflow**: Scripts work together in a pipeline
- **Flexible Inputs**: Supports various file formats, URLs, and storage backends
- **Interactive Prompts**: User-friendly prompts for missing configuration
- **Storage Agnostic**: Works with Supabase Storage, AWS S3, and more

## Installation

```bash
# Clone the repository
git clone <repository-url>
cd sync-toolkit

# Install Python dependencies
pip install -r requirements.txt
pip install -r scripts/requirements.txt

# Make scripts executable (optional)
chmod +x scripts/sync_toolkit.py
```

## Quick Start

### 1. Configure Credentials (Interactive)

The toolkit will prompt you for credentials when needed. You can also configure them upfront:

```bash
python scripts/sync_toolkit.py config
```

Credentials are stored securely in `~/.sync-toolkit/config.json` with restricted permissions.

### 2. Detect and Split Scenes

```bash
# Interactive mode (prompts for video/audio paths)
python scripts/sync_toolkit.py detect-scenes

# Or use the script directly
python scripts/video/detect_scenes.py
```

This detects scene boundaries and splits video/audio into segments.

### 3. Upload to Storage

```bash
# Upload to Supabase Storage (prompts for config if needed)
python scripts/sync_toolkit.py upload ./Scenes

# Or use the script directly
python scripts/transfer/sb_upload.py ./Scenes
```

This uploads files and creates a manifest (`uploaded_urls.txt`) with VIDEOS/AUDIOS sections.

### 4. Run Batch Lipsync Processing

```bash
# Process manifest file
python scripts/sync_toolkit.py batch --manifest uploaded_urls.txt

# Or use the script directly
python scripts/api/lipsync_batch.py --manifest uploaded_urls.txt
```

### 5. Process CSV with S3 URLs

```bash
# Process CSV file
python scripts/sync_toolkit.py process-csv --csv input.csv

# Test mode (first row only)
python scripts/sync_toolkit.py process-csv --csv input.csv --test
```

## Main Commands

### `sync_toolkit.py` - Unified CLI

```bash
# Detect and split scenes
python scripts/sync_toolkit.py detect-scenes

# Upload files to storage
python scripts/sync_toolkit.py upload [path] [--storage supabase|s3]

# Upload to S3
python scripts/sync_toolkit.py s3-upload ./Scenes s3://bucket/path/

# Download from S3
python scripts/sync_toolkit.py s3-download s3://bucket/path/ ./downloads/

# Monitor S3 uploads
python scripts/sync_toolkit.py monitor --s3-path s3://bucket/path/ --expected 100

# Run batch processing
python scripts/sync_toolkit.py batch [--manifest file.txt] [--start N] [--end M]

# Process CSV file
python scripts/sync_toolkit.py process-csv --csv file.csv [--limit N] [--test]

# Group and organize clips by faces
python scripts/sync_toolkit.py group-faces --input-dir ./clips --output-dir ./organized

# Create shots from CSV
python scripts/sync_toolkit.py create-shots --video master.mov --csv spots.csv

# Video processing utilities
python scripts/sync_toolkit.py chunk video.mov audio.wav cuts.txt ./output/
python scripts/sync_toolkit.py bounce ./videos/ --output ./bounced/
python scripts/sync_toolkit.py extract-audio ./videos/
python scripts/sync_toolkit.py rename ./output/

# Configure credentials
python scripts/sync_toolkit.py config [--clear]
```

## Individual Scripts

You can also use scripts directly:

### Video Processing

- **`detect_scenes.py`**: Detect scene boundaries and split video/audio
- **`create_shots.py`**: Create video shots from CSV spotting data
- **`group_by_face.py`**: Group and organize video clips by detected faces
- **`chunk.sh`**: Create video/audio chunks from cuts file (bash, accessible via CLI)
- **`bounce.sh`**: Create bounced versions of videos (bash, accessible via CLI)
- **`extract_audio.sh`**: Extract audio from videos (bash, accessible via CLI)

### API Processing

- **`lipsync_batch.py`**: Batch lipsync processing from manifest file
- **`s3_csv.py`**: Process CSV file with S3 URLs and submit to Sync.so

### Storage

- **`sb_upload.py`**: Upload files to Supabase Storage
- **`s3_upload.py`**: Upload files to S3 (Python, unified config)
- **`s3_download.py`**: Download files from S3 (Python, unified config)
- **`s3_monitor.py`**: Monitor S3 upload progress (Python, unified config)

## Configuration

### Credentials Storage

Credentials are stored in `~/.sync-toolkit/config.json` with restricted permissions (600). The toolkit will prompt you interactively for:

- **Sync.so API Key**: Required for API operations
- **Supabase Configuration**: Host, bucket, and service role key
- **AWS Configuration**: Access keys and region (optional if using IAM roles)

### Clearing Credentials

```bash
python scripts/sync_toolkit.py config --clear
```

## Workflow Examples

### Complete Pipeline

```bash
# 1. Detect scenes
python scripts/sync_toolkit.py detect-scenes

# 2. Upload to storage
python scripts/sync_toolkit.py upload ./Scenes

# 3. Process batch
python scripts/sync_toolkit.py batch --manifest uploaded_urls.txt
```

### CSV-Based Workflow

```bash
# 1. Process CSV with S3 URLs
python scripts/sync_toolkit.py process-csv --csv input.csv

# 2. Download results (if needed)
python scripts/transfer/download.sh --mode json sync_results.json ./outputs
```

### Face-Based Organization

```bash
# Group and organize clips by faces (single command)
python scripts/sync_toolkit.py group-faces --input-dir ./clips --output-dir ./organized
```

## Manifest Format

The `uploaded_urls.txt` manifest file format:

```
VIDEOS
https://.../public/bucket/prefix/vid_01.mov
https://.../public/bucket/prefix/vid_02.mov
...

AUDIOS
https://.../public/bucket/prefix/aud_01.wav
https://.../public/bucket/prefix/aud_02.wav
...
```

## Requirements

- Python 3.8+
- ffmpeg and ffprobe (for video processing)
- Required Python packages (see `requirements.txt` and `scripts/requirements.txt`)

## Architecture

### Unified Python Toolkit

All scripts are now Python-based with unified configuration:
- ✅ Consistent interface across all scripts
- ✅ Unified configuration system (no environment variables needed)
- ✅ Interactive prompts for missing configuration
- ✅ Shared utilities and error handling

### Shared Modules

- **`utils/config.py`**: Unified configuration management with interactive prompts
- **`utils/common.py`**: Common utilities (path handling, manifest parsing, etc.)

### Script Organization

- **`api/`**: API-related scripts (Sync.so integration)
- **`video/`**: Video processing scripts
- **`transfer/`**: Storage upload/download scripts (Python)
- **`utils/`**: Shared utilities and configuration
- **`monitor/`**: Monitoring scripts (Python)

### Bash Scripts

Some bash scripts (`.sh` files) are kept for video processing operations that work well with shell commands:
- `chunk.sh` - Video/audio chunking
- `bounce.sh` - Video bouncing
- `extract_audio.sh` - Audio extraction
- `rename.sh` - File renaming

All are accessible via the unified CLI.

## Security Notes

- Credentials are stored locally with restricted permissions
- API keys are never logged or displayed
- Use `config --clear` to remove stored credentials
- Never commit credentials to version control

## Contributing

PRs welcome! Please ensure:
- No hardcoded credentials
- Scripts work with interactive prompts
- Error handling is comprehensive
- Documentation is updated

## License

[Your License Here]
