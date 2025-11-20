#!/usr/bin/env python3
"""
Supabase Storage Uploader (No-Overwrite, Timestamped Prefix, URL manifest)
- Uploads a folder (or single file) recursively to Supabase Storage
- Remote path = <source-folder-name>_<YYYYMMDDHHMM>/<relative-file-path>
- Overwrite is DISABLED (x-upsert:false) -> never clobbers existing files
- Outputs a manifest text file listing public URLs by type (VIDEOS / AUDIOS)

Config:
- Supply Supabase host and bucket via CLI or env:
  --host / env SUPABASE_HOST  (e.g., https://your-project.supabase.co)
  --bucket / env SUPABASE_BUCKET

Auth:
  export SUPABASE_SERVICE_ROLE="..."   # recommended (server/CI)
  # or: export SUPABASE_KEY="..."      # anon/user JWT with insert perms (if policies allow)

Usage examples:
  python3 sb_upload.py "/path/to/Scenes"
  python3 sb_upload.py --host https://your.supabase.co --bucket my-bucket "/path/to/Scenes"
  # (drag & drop folder onto terminal also works)
"""

import os
import sys
import re
import time
import mimetypes
import argparse
import pathlib
import concurrent.futures as cf
from datetime import datetime
from typing import Iterable, List, Tuple, Dict
from pathlib import Path

import requests

# Add parent directory to path for utils
SCRIPT_DIR = Path(__file__).parent.parent.resolve()
sys.path.insert(0, str(SCRIPT_DIR))
from utils.config import get_config_manager
from utils.common import prompt_path, normalize_path, print_section, write_manifest, natural_sort_key

HOST = ""
BUCKET = ""

# ---------- Helpers ----------

# clean_dragdrop_path is now handled by normalize_path in utils.common

def iter_files(root: pathlib.Path) -> Iterable[pathlib.Path]:
    if root.is_file():
        # Skip AppleDouble resource fork files like '._filename'
        if not root.name.startswith('._'):
            yield root
        return
    for p in root.rglob('*'):
        if p.is_file():
            # Skip AppleDouble resource fork files like '._filename'
            if p.name.startswith('._'):
                continue
            yield p

# slugify_name is now handled by slugify in utils.common
from utils.common import slugify as slugify_name

def rel_path(file_path: pathlib.Path, base: pathlib.Path) -> str:
    return file_path.relative_to(base).as_posix() if base.is_dir() else file_path.name

def guess_mime(path: pathlib.Path) -> str:
    m, _ = mimetypes.guess_type(str(path))
    return m or 'application/octet-stream'

def is_video_mime(m: str) -> bool:
    return m.startswith('video/')

def is_audio_mime(m: str) -> bool:
    return m.startswith('audio/')

def build_public_url(remote_path: str) -> str:
    return f"{HOST}/storage/v1/object/public/{BUCKET}/{remote_path}"

def supabase_upload(
    local_path: pathlib.Path,
    remote_path: str,
    key: str,
    content_type: str,
    timeout_s: float = 120.0,
    max_retries: int = 4
) -> Tuple[bool, str]:
    """
    POST to /storage/v1/object/{bucket}/{path} with x-upsert:false.
    Returns (ok, msg_or_url). On success -> public URL.
    """
    url = f"{HOST}/storage/v1/object/{BUCKET}/{remote_path}"
    headers = {
        "Authorization": f"Bearer {key}",
        "Content-Type": content_type,
        "x-upsert": "false"  # NEVER overwrite
    }

    attempt = 0
    backoff = 1.0
    while True:
        attempt += 1
        try:
            with open(local_path, "rb") as f:
                resp = requests.post(url, headers=headers, data=f, timeout=timeout_s)
            if 200 <= resp.status_code < 300:
                return True, build_public_url(remote_path)
            # 409 Conflict = already exists (as designed, we won't overwrite)
            if resp.status_code == 409:
                return False, f"Conflict (exists): {remote_path}"
            msg = f"HTTP {resp.status_code}: {resp.text[:300]}"
        except requests.RequestException as e:
            msg = f"REQ_ERR: {e}"

        if attempt >= max_retries:
            return False, f"Failed after {attempt} tries: {msg}"
        time.sleep(backoff)
        backoff = min(backoff * 2, 8.0)

# natural_key is now imported from utils.common

# ---------- Main ----------

def main():
    parser = argparse.ArgumentParser(description="Upload to Supabase Storage without overwrite; timestamped prefix; write URL manifest.")
    parser.add_argument("path", nargs="?", help="Folder or file to upload (supports drag & drop if omitted).")
    parser.add_argument("--concurrency", type=int, default=4, help="Parallel uploads (default 4).")
    parser.add_argument("--timeout", type=float, default=120.0, help="Per-request timeout seconds.")
    parser.add_argument("--dry-run", action="store_true", help="List planned uploads; do not send.")
    parser.add_argument("--host", default=None, help="Supabase project host, e.g. https://xyz.supabase.co")
    parser.add_argument("--bucket", default=None, help="Supabase storage bucket name")
    args = parser.parse_args()

    # Get Supabase configuration (prompts if needed)
    config_manager = get_config_manager()
    storage_config = config_manager.get_supabase_config(prompt=True)
    
    # Resolve Host/Bucket
    global HOST, BUCKET
    HOST = (args.host or storage_config.supabase_host or "").strip().rstrip("/")
    BUCKET = (args.bucket or storage_config.supabase_bucket or "").strip()
    
    if not HOST or not BUCKET:
        print("Error: Supabase host and bucket are required.", file=sys.stderr)
        print("Please provide via --host/--bucket flags or configure interactively.", file=sys.stderr)
        sys.exit(2)

    # Get API key
    key = storage_config.supabase_key
    if not key:
        print("Error: Supabase service role key is required.", file=sys.stderr)
        sys.exit(2)

    # Input path (prompt if missing)
    if args.path:
        base = normalize_path(args.path)
    else:
        base = prompt_path("Enter folder or file to upload", must_exist=True)
    
    if not base.exists():
        print(f"Not found: {base}", file=sys.stderr)
        sys.exit(2)

    # Build file list
    files: List[pathlib.Path] = list(iter_files(base))
    if not files:
        print("No files found.", file=sys.stderr)
        sys.exit(3)

    # Build unique remote prefix: <folder-name>_<YYYYMMDDHHMM>
    src_folder_name = base.name if base.is_dir() else base.parent.name or base.stem
    src_folder_name = slugify_name(src_folder_name) or "upload"
    ts = datetime.now().strftime("%Y%m%d%H%M")
    remote_prefix = f"{src_folder_name}_{ts}"

    # Prepare tasks
    tasks = []
    for fp in files:
        rel = rel_path(fp, base)
        remote_path = f"{remote_prefix}/{rel}"
        # clean accidental '//' (just in case)
        remote_path = re.sub(r"/{2,}", "/", remote_path)
        ctype = guess_mime(fp)
        tasks.append((fp, remote_path, ctype))

    # Dry run view
    if args.dry_run:
        print(f"[DRY RUN] Would upload {len(tasks)} file(s) to {BUCKET}/{remote_prefix} (no-overwrite):")
        for fp, rp, ct in sorted(tasks, key=lambda t: natural_key(t[1])):
            print(f"- {fp} -> {rp} ({ct})")
        print("\nRemote base prefix:", remote_prefix)
        sys.exit(0)

    print(f"Uploading {len(tasks)} file(s) to bucket '{BUCKET}' under '{remote_prefix}' (no overwrite)...\n")

    # Upload with concurrency
    ok_urls: Dict[str, List[str]] = {"video": [], "audio": []}
    failures: List[str] = []

    def do_task(item):
        fp, rp, ct = item
        ok, msg = supabase_upload(fp, rp, key, ct, timeout_s=args.timeout)
        return fp, rp, ct, ok, msg

    with cf.ThreadPoolExecutor(max_workers=max(1, args.concurrency)) as ex:
        for fp, rp, ct, ok, msg in ex.map(do_task, tasks):
            if ok:
                print(f"✓ {fp.name} → {rp}")
                if is_video_mime(ct):
                    ok_urls["video"].append(build_public_url(rp))
                elif is_audio_mime(ct):
                    ok_urls["audio"].append(build_public_url(rp))
                else:
                    # not requested, but log for visibility
                    pass
            else:
                print(f"✗ {fp.name} → {rp}\n   {msg}", file=sys.stderr)
                failures.append(f"{rp} :: {msg}")

    # Sort URLs naturally by filename portion
    def sort_by_filename(urls: List[str]) -> List[str]:
        return sorted(urls, key=lambda u: natural_sort_key(u.rsplit('/', 1)[-1]))

    video_urls = sort_by_filename(ok_urls["video"])
    audio_urls = sort_by_filename(ok_urls["audio"])

    # Write manifest text file in the current working directory
    out_dir = Path.cwd()
    manifest_path = out_dir / "uploaded_urls.txt"
    write_manifest(video_urls, audio_urls, manifest_path)

    print("\n--- Upload complete ---")
    print(f"Remote base prefix: {remote_prefix}")
    print(f"Manifest written: {manifest_path}")
    if failures:
        print(f"Failures: {len(failures)} (see stderr lines above)")

if __name__ == "__main__":
    # Common media types
    mimetypes.add_type("video/quicktime", ".mov")
    mimetypes.add_type("video/mp4", ".mp4")
    mimetypes.add_type("audio/wav", ".wav")
    mimetypes.add_type("audio/mpeg", ".mp3")
    mimetypes.add_type("audio/mp4", ".m4a")
    main()