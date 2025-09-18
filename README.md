## Sync Toolkit — Scripts for Sync.so Bulk Lipsync Workflows

This repository is a collection of practical scripts to automate end‑to‑end bulk lipsync clip generation using the Sync.so API. It covers scene detection/splitting, uploading to object storage, batch generation via the Sync Generate API, and downloading results.

### What’s Included
- `detect_scenes.py`: Detects scene boundaries using ffmpeg and PySceneDetect, writes a CSV, and splits video/audio into segments.
- `sb_upload.py`: Uploads a file/folder to Supabase Storage with a timestamped prefix. It never overwrites existing files and produces a URL manifest grouped as `VIDEOS` / `AUDIOS` for downstream batching.
- `lipsync_batch.py`: Reads the URL manifest, submits multiple lipsync jobs in parallel to Sync.so, polls for completion, and downloads the outputs.

All scripts avoid hardcoding secrets. Provide configuration via environment variables, CLI flags, or a local `.env` file.

### Quickstart
1) Install requirements
```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

2) Copy and edit environment variables
```bash
cp .env.example .env
# edit .env with your keys and hosts
```

3) Detect scenes and split media (optional but recommended)
```bash
python detect_scenes.py
# Follow the prompt to drop your source video (and optional matching WAV)
```

4) Upload segments to storage and create a manifest
```bash
# Example using Supabase Storage
python sb_upload.py --host "$SUPABASE_HOST" --bucket "$SUPABASE_BUCKET" ./Scenes
# Produces uploaded_urls.txt with VIDEOS/AUDIOS sections
```

5) Run bulk lipsync generation
```bash
export SYNC_API_KEY="your_sync_api_key"
python lipsync_batch.py --manifest ./uploaded_urls.txt --max-workers 15
```

Outputs are saved to `./outputs`. Adjust `--start/--end` to subset indices.

### Configuration
Environment variables (use `.env` or export in your shell):
- `SYNC_API_KEY`: Sync.so API key for Generate API.
- `SUPABASE_HOST`: Your Supabase project host, e.g. `https://xyzcompany.supabase.co`.
- `SUPABASE_BUCKET`: Supabase Storage bucket name for uploads.
- `SUPABASE_SERVICE_ROLE` or `SUPABASE_KEY`: Credential used by `sb_upload.py`. Service role is recommended for server/CI; a scoped anon/user JWT with insert permissions can work if policies allow.

CLI flags:
- `sb_upload.py`: `--host`, `--bucket`, `--concurrency`, `--timeout`, `--dry-run`, `--key-env`.
- `lipsync_batch.py`: `--manifest`, `--start`, `--end`, `--max-workers`, `--no-exists-check`, `--keep-asd`, `--verbose`.

### Notes
- `detect_scenes.py` requires `ffmpeg` and `ffprobe` on your PATH. PySceneDetect is optional but improves cut detection.
- `sb_upload.py` uses no‑overwrite semantics; existing objects are preserved.
- `lipsync_batch.py` includes adaptive retry/backoff and can reduce concurrency when errors occur.

### Example Manifest Format (uploaded_urls.txt)
```
VIDEOS
https://.../public/bucket/prefix/vid_01.mov
...

AUDIOS
https://.../public/bucket/prefix/aud_01.wav
...
```

### Suggested Additional Scripts
- `sync_upload.py`: Directly upload local files to Sync.so’s transient storage (if available) and return signed URLs for immediate use.
- `verify_pairs.py`: Validate manifest URL pairs (content‑type, duration windows, presence) before submission.
- `rename_pairs.py`: Bulk rename local files to a consistent pattern `vid_XX`/`aud_XX` before upload.
- `concat_outputs.py`: Concatenate completed outputs back into a single timeline using `ffmpeg`.
- `webhook_worker.py`: Flask/FastAPI listener for Sync.so webhooks to download results asynchronously.
- `resubmit_failed.py`: Parse a `lipsync_batch` log and resubmit failed indices only.

PRs welcome. Please avoid committing real keys or project‑specific hosts in code or history.


