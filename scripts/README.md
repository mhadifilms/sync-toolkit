# sync. toolkit scripts

This directory contains all scripts for the Sync Toolkit, organized by functionality.

## Structure

```
scripts/
├── api/              # API-related scripts (Sync.so integration)
├── video/            # Video processing scripts
├── transfer/         # Storage upload/download scripts
├── monitor/          # Monitoring scripts
├── utils/            # Shared utilities and configuration
└── sync_toolkit.py   # Main unified CLI entry point
```

## Unified CLI

All scripts are accessible through the main CLI:

```bash
python scripts/sync_toolkit.py <command> [options]
```

## Script Categories

### API Scripts (`api/`)

- **`lipsync_batch.py`**: Batch lipsync processing from manifest file
- **`s3_csv.py`**: Process CSV file with S3 URLs and submit to Sync.so

### Video Processing (`video/`)

**Python Scripts:**
- **`detect_scenes.py`**: Detect scene boundaries and split video/audio
- **`create_shots.py`**: Create video shots from CSV spotting data
- **`group_by_face.py`**: Group and organize video clips by detected faces

**Bash Scripts (accessible via CLI):**
- **`chunk.sh`**: Create video/audio chunks from cuts file
- **`bounce.sh`**: Create bounced versions of videos
- **`extract_audio.sh`**: Extract audio from videos

### Storage (`transfer/`)

**Python Scripts:**
- **`sb_upload.py`**: Upload files to Supabase Storage
- **`s3_upload.py`**: Upload files to S3 (unified config)
- **`s3_download.py`**: Download files from S3 (unified config)

### Monitoring (`monitor/`)

**Python Scripts:**
- **`s3_monitor.py`**: Monitor S3 upload progress (unified config)

### Utilities (`utils/`)

**Python Modules:**
- **`config.py`**: Unified configuration management
- **`common.py`**: Shared utilities and helpers
- **`timecode.py`**: Timecode conversion utilities (supports any frame rate: 24, 23.976, 25, 29.97, 30, 50, 59.94, 60, etc.)

**Bash Scripts:**
- **`common.sh`**: Common bash utilities (library, used by bash scripts)
- **`rename.sh`**: Rename files sequentially (accessible via CLI as `rename`)

## Usage Patterns

### Via Unified CLI (Recommended)

```bash
# All scripts accessible through main CLI
python scripts/sync_toolkit.py <command> [options]
```

### Direct Script Usage

```bash
# Python scripts can be run directly
python scripts/api/lipsync_batch.py --manifest urls.txt

# Bash scripts can be run directly
bash scripts/video/chunk.sh video.mov audio.wav cuts.txt ./output/
```

## Configuration

All Python scripts use the unified configuration system:
- Credentials stored in `~/.sync-toolkit/config.json`
- Interactive prompts for missing configuration
- No environment variables required

Bash scripts may still use environment variables or command-line arguments.

## Video Processing Scripts

Video processing bash scripts (`chunk.sh`, `bounce.sh`, `extract_audio.sh`) are kept as-is because they:
- Use complex ffmpeg operations that are easier in bash
- Are well-tested and stable
- Are accessible via the unified CLI

They may be converted to Python in the future for full consistency.

## Adding New Scripts

When adding new scripts:

1. **Use Python** for new scripts
2. **Use unified config** (`utils/config.py`)
3. **Use shared utilities** (`utils/common.py`)
4. **Add to main CLI** (`sync_toolkit.py`)
5. **Follow existing patterns** for consistency

## Dependencies

### Python Scripts
- `requests` - HTTP operations
- `boto3` - AWS S3 operations
- `tqdm` - Progress bars
- `scenedetect` - Scene detection (optional)

### Bash Scripts
- `ffmpeg` / `ffprobe` - Video processing
- `aws` CLI - S3 operations (if using S3 features)
- Standard Unix utilities

See `requirements.txt` and `scripts/requirements.txt` for full dependency lists.
