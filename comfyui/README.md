# ComfyUI Custom Nodes for Sync Toolkit

This directory contains ComfyUI custom nodes that wrap sync-toolkit functions, enabling node-based workflow processing.

## Installation

1. **Install sync-toolkit dependencies:**
   ```bash
   pip install -r ../scripts/requirements.txt
   ```

2. **Install ComfyUI nodes:**
   ```bash
   python comfyui/install.py
   ```
   
   This will create a symlink (or copy) from ComfyUI's `custom_nodes` directory to this `comfyui` directory.

3. **Restart ComfyUI** to load the new nodes.

## Available Nodes

### Configuration
- **Credentials** - Manage credentials (API keys, AWS keys, Supabase keys) - use this node once and connect to all other nodes

### Video Processing
- **Detect Scenes** - Detect scene boundaries and split video/audio
- **Create Shots** - Create video shots from CSV spotting data
- **Group By Face** - Group video clips by detected faces
- **Extract Audio** - Extract audio from videos
- **Bounce Video** - Create bounced versions of videos
- **Chunk Video** - Create video/audio chunks from cuts file

### Storage/Transfer
- **Upload To Storage** - Upload files to S3 or Supabase Storage (combined node)
  - Settings: bucket names, S3 paths, parallel uploads, etc.
- **S3 Download** - Download files from S3
- **S3 Monitor** - Monitor S3 upload progress

### API Processing
- **Lipsync Batch** - Run batch lipsync processing from manifest
- **Process CSV** - Process CSV file or URL lists for Sync.so API

### Utility
- **Convert Timecode** - Convert timecodes between frame rates (single or CSV)
- **Rename Files** - Rename files sequentially in a directory

## Credentials

**Use the Credentials node** to manage all credentials in one place:

1. Create a **Credentials** node and enter your credentials (or leave empty to use environment variables)
2. Connect the `credentials` output to the `credentials` input of any node that needs authentication
3. Each node still has its own **settings** (like which S3 bucket/folder to use, region, etc.)

If credentials are not provided via the Credentials node, nodes will fall back to:
- **AWS S3**: System SSO/IAM roles, environment variables (`AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`), or `~/.aws/credentials`
- **Supabase**: Environment variables (`SUPABASE_HOST`, `SUPABASE_BUCKET`, `SUPABASE_KEY`)
- **Sync API**: Environment variable (`SYNC_API_KEY`)

## Node Connectivity

Nodes are designed to connect seamlessly:

- `manifest_path` output → connects to `LipsyncBatch.manifest_path` input
- `output_directory` output → connects to any node expecting directory input
- `csv_path` output → connects to `CreateShots.csv_path`, `ConvertTimecode.csv_path`
- `results_json` output → connects to `S3Download` (json mode)

## Flexible Inputs

- **UploadToStorage**: Accepts directory path (STRING) or JSON list of file paths
- **ProcessCSV**: Can take CSV file path OR separate video/audio URL lists (JSON strings)
- **ConvertTimecode**: Single timecode string OR CSV file path

## Live Updates

When installed via symlink (default), changes to nodes will be reflected immediately in ComfyUI. To force a copy instead of symlink:

```bash
python comfyui/install.py --copy
```

## Troubleshooting

- **Import errors**: Ensure sync-toolkit scripts directory is accessible
- **Credential errors**: Check environment variables or provide credentials per-node
- **Path errors**: All paths are normalized automatically, but ensure files/directories exist

