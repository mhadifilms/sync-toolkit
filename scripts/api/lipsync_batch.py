#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Parallel lipsync via Sync Generate API using URL inputs.

- Scans fixed indices 01..28 by default (skips 00)
- Builds pairs from a manifest file uploaded_urls.txt (VIDEOS / AUDIOS sections)
- Submits each pair with model lipsync-2-pro
- Enables obstruction detection and (if available) active speaker detection
- Runs multiple jobs concurrently, polls to completion, downloads outputs

Usage:
  export SYNC_API_KEY="YOUR_KEY"
  python lipsync_batch.py --max-workers 15

Args:
  --manifest        Path to uploaded_urls.txt (default: ./uploaded_urls.txt)
  --start           Start index (default: 1)
  --end             End index inclusive (default: 28)
  --max-workers     Max parallel jobs (default: 15, clamped to [1,15])
  --no-exists-check Skip pre-flight HEAD/GET existence checks (faster, risk 404)
  --keep-asd        Force active_speaker=True (no fallback off on 400 errors)
  --verbose         More logging

Requirements: pip install requests tqdm
"""

import os
import sys
import time
import json
import logging
import argparse
from pathlib import Path
from typing import Optional, Dict, Any, Tuple, List
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests
from tqdm import tqdm

# Add parent directory to path for utils
SCRIPT_DIR = Path(__file__).parent.parent.resolve()
sys.path.insert(0, str(SCRIPT_DIR))
from utils.config import get_config_manager
from utils.common import parse_manifest, prompt_path, print_section

API_BASE = "https://api.sync.so/v2"
GENERATE_URL = f"{API_BASE}/generate"
GET_URL = f"{API_BASE}/generate/{{id}}"

# ---- Defaults ----
AUDIO_FMT = "aud_{:02d}.wav"  # kept for logging
VIDEO_FMT = "vid_{:02d}.mov"  # kept for logging
OUTDIR = Path("./outputs")

# Networking & polling behavior
TIMEOUT = 30                 # per-request timeout seconds
POLL_EVERY_SEC = 6           # poll cadence
MAX_RETRIES_429 = 6          # exponential backoff tries on 429
MAX_RETRIES_5XX = 5          # retries on transient 5xx (e.g., 502/503/504)
HEADERS = {"Content-Type": "application/json"}

# Options: obstruction detection + active speaker (fallback if unknown)
LIPSYNC_OPTIONS_BASE: Dict[str, Any] = {
    "sync_mode": "cut_off",
    "occlusion_detection_enabled": True,
    "active_speaker": True,
}

# ------------------ HTTP helpers ------------------

def backoff_sleep(attempt: int) -> None:
    delay = min(2 ** attempt, 30)
    time.sleep(delay)

def post_json(url: str, payload: Dict[str, Any], headers: Dict[str, str]) -> requests.Response:
    attempt = 0
    while True:
        try:
            r = requests.post(url, headers=headers, json=payload, timeout=TIMEOUT)
        except requests.RequestException as e:
            # Network error: retry as a transient failure
            if attempt >= MAX_RETRIES_5XX:
                raise
            attempt += 1
            logging.warning("POST error %s; retrying (%d/%d) ...", e, attempt, MAX_RETRIES_5XX)
            backoff_sleep(attempt)
            continue

        # 429 Too Many Requests: honor Retry-After if present
        if r.status_code == 429:
            if attempt >= MAX_RETRIES_429:
                return r
            attempt += 1
            retry_after = r.headers.get("retry-after")
            if retry_after and retry_after.isdigit():
                time.sleep(int(retry_after))
            else:
                backoff_sleep(attempt)
            continue

        # Retry on 5xx transient server errors (e.g., 502/503/504)
        if 500 <= r.status_code < 600:
            if attempt >= MAX_RETRIES_5XX:
                return r
            attempt += 1
            logging.warning("POST %s -> %d; retrying (%d/%d) ...", url, r.status_code, attempt, MAX_RETRIES_5XX)
            backoff_sleep(attempt)
            continue

        return r

def get_json(url: str, headers: Dict[str, str]) -> requests.Response:
    attempt = 0
    while True:
        try:
            r = requests.get(url, headers=headers, timeout=TIMEOUT)
        except requests.RequestException as e:
            # Network error: retry as a transient failure
            if attempt >= MAX_RETRIES_5XX:
                raise
            attempt += 1
            logging.warning("GET error %s; retrying (%d/%d) ...", e, attempt, MAX_RETRIES_5XX)
            backoff_sleep(attempt)
            continue

        # 429 Too Many Requests: honor Retry-After if present
        if r.status_code == 429:
            if attempt >= MAX_RETRIES_429:
                return r
            attempt += 1
            retry_after = r.headers.get("retry-after")
            if retry_after and retry_after.isdigit():
                time.sleep(int(retry_after))
            else:
                backoff_sleep(attempt)
            continue

        # Retry on 5xx transient server errors (e.g., 502/503/504)
        if 500 <= r.status_code < 600:
            if attempt >= MAX_RETRIES_5XX:
                return r
            attempt += 1
            logging.warning("GET %s -> %d; retrying (%d/%d) ...", url, r.status_code, attempt, MAX_RETRIES_5XX)
            backoff_sleep(attempt)
            continue

        return r

def check_url_exists(url: str) -> bool:
    """HEAD, with Range fallback for hosts that block HEAD."""
    try:
        r = requests.head(url, timeout=TIMEOUT, allow_redirects=True)
        if r.status_code == 200:
            return True
        if r.status_code in (403, 405):
            r = requests.get(url, headers={"Range": "bytes=0-0"}, timeout=TIMEOUT, stream=True)
            return r.status_code in (200, 206)
        return False
    except requests.RequestException:
        return False

def download_file(url: str, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    with requests.get(url, stream=True, timeout=120) as r:
        r.raise_for_status()
        total = int(r.headers.get("content-length", 0))
        with open(dest, "wb") as f, tqdm(
            total=total, unit="B", unit_scale=True, unit_divisor=1024, desc=dest.name
        ) as bar:
            for chunk in r.iter_content(chunk_size=1024 * 256):
                if chunk:
                    f.write(chunk)
                    bar.update(len(chunk))

# ------------------ Sync API helpers ------------------

def submit_generation(
    api_key: str,
    video_url: str,
    audio_url: str,
    output_name: str,
    allow_asd: bool = True,
) -> Dict[str, Any]:
    headers = {**HEADERS, "x-api-key": api_key}

    options = dict(LIPSYNC_OPTIONS_BASE)
    if not allow_asd:
        options.pop("active_speaker", None)

    payload = {
        "model": "lipsync-2-pro",
        "input": [
            {"type": "video", "url": video_url},
            {"type": "audio", "url": audio_url},
        ],
        "options": options,
        "outputFileName": output_name,
    }

    r = post_json(GENERATE_URL, payload, headers)
    if r.status_code == 201:
        return r.json()

    # If server rejects an unknown/locked option (often active_speaker), retry once without it.
    try:
        body = r.json()
    except Exception:
        body = {"error": r.text}

    error_text = json.dumps(body)
    if r.status_code == 400 and allow_asd and ("active" in error_text.lower() or "unknown" in error_text.lower()):
        logging.warning("[%s] active_speaker not available on this key; retrying without it.", output_name)
        return submit_generation(api_key, video_url, audio_url, output_name, allow_asd=False)

    raise RuntimeError(f"[{output_name}] Create failed ({r.status_code}): {error_text}")

def poll_until_complete(api_key: str, job_id: str, label: str) -> Dict[str, Any]:
    headers = {**HEADERS, "x-api-key": api_key}
    while True:
        r = get_json(GET_URL.format(id=job_id), headers)
        if r.status_code != 200:
            raise RuntimeError(f"[{label}] Poll failed ({r.status_code}): {r.text}")
        gen = r.json()
        status = (gen.get("status") or "").upper()
        if status in ("COMPLETED", "FAILED", "REJECTED"):
            return gen
        time.sleep(POLL_EVERY_SEC)

# ------------------ Worker ------------------

def process_index(
    idx: int,
    api_key: str,
    video_urls: List[str],
    audio_urls: List[str],
    check_exists: bool,
    force_asd: bool,
) -> Tuple[int, str]:
    """
    Returns (idx, status_str). status_str is 'completed', 'skipped', or 'failed:<msg>'
    """
    # Bounds check against manifest lists (1-indexed indices)
    if idx <= 0 or idx > len(video_urls) or idx > len(audio_urls):
        logging.warning("[SKIP %02d] index out of range for manifest (v=%d, a=%d)", idx, len(video_urls), len(audio_urls))
        return idx, "skipped"

    vid_url = video_urls[idx - 1]
    aud_url = audio_urls[idx - 1]
    out_name = f"out_{idx:02d}"

    if check_exists:
        v_ok = check_url_exists(vid_url)
        a_ok = check_url_exists(aud_url)
        if not (v_ok and a_ok):
            miss = []
            if not v_ok: miss.append("video")
            if not a_ok: miss.append("audio")
            logging.warning("[SKIP %02d] missing %s", idx, "/".join(miss))
            return idx, "skipped"

    logging.info("[SUBMIT %02d] %s + %s -> %s.mp4", idx, VIDEO_FMT.format(idx), AUDIO_FMT.format(idx), out_name)
    try:
        resp = submit_generation(api_key, vid_url, aud_url, out_name, allow_asd=force_asd or True)
        job_id = resp.get("id")
        if not job_id:
            raise RuntimeError("No job id in response.")
        logging.info("[POLL  %02d] id=%s …", idx, job_id)
        gen = poll_until_complete(api_key, job_id, out_name)
        status = (gen.get("status") or "").upper()
        if status != "COMPLETED":
            err = gen.get("error") or gen
            logging.error("[FAIL  %02d] status=%s | %s", idx, status, err)
            return idx, f"failed:{status}"

        output_url = gen.get("outputUrl") or gen.get("output_url")
        if not output_url:
            logging.error("[FAIL  %02d] Completed but no output URL", idx)
            return idx, "failed:no_output_url"

        dest = OUTDIR / f"{out_name}.mp4"
        logging.info("[DL    %02d] -> %s", idx, dest)
        download_file(output_url, dest)
        return idx, "completed"

    except Exception as e:
        logging.exception("[EXC   %02d] %s", idx, e)
        return idx, f"failed:{e}"

# ------------------ Main ------------------

def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Parallel Sync lipsync URL batcher (manifest-based)")
    p.add_argument("--manifest", default=None, help="Path to uploaded_urls.txt containing VIDEOS/AUDIOS URLs")
    p.add_argument("--start", type=int, default=1, help="Start index (inclusive)")
    p.add_argument("--end", type=int, default=28, help="End index (inclusive)")
    p.add_argument("--max-workers", type=int, default=15, help="Parallel jobs (clamped to 1..15)")
    p.add_argument("--no-exists-check", action="store_true", help="Skip existence checks (faster; risk 404)")
    p.add_argument("--keep-asd", action="store_true", help="Force active_speaker=True; don't retry without it")
    p.add_argument("--verbose", action="store_true", help="Verbose logging")
    return p.parse_args()

# parse_manifest is now imported from utils.common

def main() -> None:
    args = parse_args()
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s | %(levelname)s | %(message)s"
    )

    # Get API key from config manager (prompts if needed)
    config_manager = get_config_manager()
    api_key = config_manager.get_sync_api_key(prompt=True)
    if not api_key:
        print("ERROR: Sync API key is required.", file=sys.stderr)
        sys.exit(1)

    # Set default end if not provided
    if not args.end:
        args.end = 28  # Default end index
    
    if args.start < 1 or args.end < args.start:
        print("ERROR: invalid start/end range.", file=sys.stderr)
        sys.exit(2)

    # Clamp workers to [1, 15]
    workers = max(1, min(int(args.max_workers), 15))

    # Read manifest and build URL lists
    if args.manifest:
        manifest_path = Path(args.manifest).expanduser().resolve()
    else:
        # Prompt for manifest if not provided
        manifest_path = prompt_path("Enter path to manifest file (uploaded_urls.txt)", must_exist=True)
    
    try:
        video_urls, audio_urls = parse_manifest(manifest_path)
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(3)
    if not video_urls or not audio_urls:
        print("ERROR: No video/audio URLs found in manifest.", file=sys.stderr)
        sys.exit(4)

    # Clamp indices to available pairs in manifest to avoid permanent skips
    max_pairs = min(len(video_urls), len(audio_urls))
    if args.end > max_pairs:
        logging.warning("End index %d exceeds available pairs %d; clamping to %d.", args.end, max_pairs, max_pairs)
    end_idx = min(args.end, max_pairs)

    OUTDIR.mkdir(exist_ok=True)
    all_indices = list(range(args.start, end_idx + 1))
    logging.info("Processing indices: %s", ", ".join(f"{i:02d}" for i in all_indices))
    logging.info("Manifest: %s | Workers: %d", manifest_path, workers)

    # Adaptive retry loop: keep going until all indices complete
    pending = list(all_indices)
    completed: List[int] = []
    attempts: Dict[int, int] = {}
    current_workers = workers

    while pending:
        round_indices = list(pending)
        failed_this_round: List[int] = []
        logging.info("Round start: pending=%d | workers=%d", len(round_indices), current_workers)
        with ThreadPoolExecutor(max_workers=current_workers) as ex:
            futures = {
                ex.submit(
                    process_index,
                    idx=i,
                    api_key=api_key,
                    video_urls=video_urls,
                    audio_urls=audio_urls,
                    check_exists=(not args.no_exists_check),
                    force_asd=args.keep_asd,
                ): i for i in round_indices
            }

            for fut in as_completed(futures):
                idx = futures[fut]
                try:
                    i, status = fut.result()
                except Exception as e:
                    logging.exception("[JOIN  %02d] %s", idx, e)
                    attempts[idx] = attempts.get(idx, 0) + 1
                    failed_this_round.append(idx)
                    continue

                if status == "completed":
                    completed.append(i)
                else:
                    attempts[i] = attempts.get(i, 0) + 1
                    failed_this_round.append(i)

        # Rebuild pending (remove completed)
        pending = [i for i in pending if i not in completed]

        if not pending:
            break

        # Adaptive backoff and worker reduction if there were failures
        if failed_this_round:
            # Reduce workers to ease pressure on upstream, down to 1
            if current_workers > 1:
                current_workers = max(1, current_workers - 1)
                logging.warning("Failures detected; reducing workers to %d", current_workers)
            # Sleep with exponential backoff based on max attempts for failed ones
            max_attempts = max(attempts.get(i, 1) for i in failed_this_round)
            sleep_s = min(30, 2 ** min(max_attempts, 4))
            logging.info("Retrying %d item(s) after %ds: %s", len(pending), sleep_s, ", ".join(f"{i:02d}" for i in pending))
            time.sleep(sleep_s)

    # Final summary
    completed.sort()
    logging.info("=== SUMMARY ===")
    logging.info("Completed: %s", ", ".join(f"{i:02d}" for i in completed) if completed else "—")

if __name__ == "__main__":
    main()