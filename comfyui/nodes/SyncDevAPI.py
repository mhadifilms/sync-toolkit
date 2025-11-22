"""
ComfyUI node for Sync.so Dev API processing.
Handles dev API which creates folders for each job ID.
Monitors S3 outputs and downloads them organized by job ID.
"""
import sys
import json
import time
import requests
from pathlib import Path
from typing import List, Dict, Any, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed

# Add current directory (comfyui) to path for utils import
COMFYUI_DIR = Path(__file__).parent.parent
if str(COMFYUI_DIR) not in sys.path:
    sys.path.insert(0, str(COMFYUI_DIR))

# Add project root to path
PROJECT_ROOT = COMFYUI_DIR.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Add scripts directory to path
SCRIPT_DIR = PROJECT_ROOT / "scripts"
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

# Import utils from comfyui directory using importlib to avoid conflict with scripts/utils
import importlib.util
utils_path = COMFYUI_DIR / "utils.py"
utils_spec = importlib.util.spec_from_file_location("comfyui_utils", utils_path)
_comfyui_utils = importlib.util.module_from_spec(utils_spec)
utils_spec.loader.exec_module(_comfyui_utils)

normalize_path = _comfyui_utils.normalize_path
ensure_absolute_path = _comfyui_utils.ensure_absolute_path
format_error = _comfyui_utils.format_error
get_sync_api_key = _comfyui_utils.get_sync_api_key
get_s3_client = _comfyui_utils.get_s3_client
parse_json_string = _comfyui_utils.parse_json_string


class SyncDevAPI:
    """Process videos through Sync.so Dev API with job ID folder organization"""
    
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "input_type": (["manifest", "requests"], {"default": "manifest"}),
            },
            "optional": {
                "manifest_path": ("STRING", {"default": ""}),
                "requests_json": ("STRING", {"default": ""}),  # From LipsyncBatch node
                "credentials": ("CREDENTIALS", {"default": None}),
                "api_endpoint": ("STRING", {"default": "https://api.sync.so/v2/generate"}),  # Dev API endpoint
                "output_base_dir": ("STRING", {"default": ""}),  # Base directory for downloads
                "s3_output_base": ("STRING", {"default": ""}),  # S3 base path where outputs are stored
                "max_workers": ("INT", {"default": 15, "min": 1, "max": 15}),
                "monitor_interval": ("INT", {"default": 180, "min": 10}),  # Seconds between S3 checks
                "download_outputs": ("BOOLEAN", {"default": True}),  # Download completed outputs
            }
        }
    
    RETURN_TYPES = ("INT", "DIRECTORY_DATA", "STRING", "STRING")
    RETURN_NAMES = ("completed_count", "output_directory", "results_json", "job_ids_json")
    FUNCTION = "run"
    CATEGORY = "sync-toolkit/api"
    
    def run(self, input_type: str, manifest_path: str = "", requests_json: str = "",
            credentials: dict = None,
            api_endpoint: str = "https://api.sync.so/v2/generate",
            output_base_dir: str = "", s3_output_base: str = "",
            max_workers: int = 15,
            monitor_interval: int = 180, download_outputs: bool = True):
        """Run dev API processing"""
        try:
            creds = credentials or {}
            api_key = creds.get("sync_api_key", "") or get_sync_api_key("")
            if not api_key:
                return (0, {"error": "ERROR: Sync API key required"}, "", "")
            
            aws_access_key_id = creds.get("aws_access_key_id", "")
            aws_secret_key = creds.get("aws_secret_access_key", "")
            aws_region = creds.get("aws_region", "us-east-1")
            use_sso = creds.get("use_sso", False)
            
            # Get S3 client for monitoring/downloading
            s3_client = None
            if s3_output_base or download_outputs:
                try:
                    s3_client = get_s3_client(
                        aws_region,
                        aws_access_key_id if not use_sso else None,
                        aws_secret_key if not use_sso else None
                    )
                except Exception as e:
                    return (0, {"error": f"ERROR: Failed to initialize S3 client: {format_error(e)}"}, "", "")
            
            # Parse manifest
            manifest_file = normalize_path(manifest_path)
            if not manifest_file.exists():
                return (0, {"error": "ERROR: Manifest file not found"}, "", "")
            
            from utils.common import parse_manifest
            video_urls, audio_urls = parse_manifest(manifest_file)
            
            if not video_urls or not audio_urls:
                return (0, {"error": "ERROR: No video/audio URLs found in manifest"}, "", "")
            
            # Set end index
            if end_index == 0:
                end_index = min(len(video_urls), len(audio_urls))
            
            max_pairs = min(len(video_urls), len(audio_urls))
            end_idx = min(end_index, max_pairs)
            
            if start_index < 1 or end_idx < start_index:
                return (0, {"error": "ERROR: Invalid start/end range"}, "", "")
            
            # Set output directory
            if output_base_dir:
                output_dir = normalize_path(output_base_dir)
            else:
                output_dir = manifest_file.parent / "dev_api_outputs"
            output_dir.mkdir(parents=True, exist_ok=True)
            
            # Process indices
            all_indices = list(range(start_index, end_idx + 1))
            results = []
            job_ids = {}
            
            # Submit all jobs
            headers = {
                "x-api-key": api_key,
                "Content-Type": "application/json"
            }
            
            def submit_job(idx: int) -> tuple:
                try:
                    aud_url = audio_urls[idx - 1]
                    
                    payload = {
                        "model": "lipsync-2-pro",
                        "input": [
                            {"type": "video", "url": vid_url},
                            {"type": "audio", "url": aud_url}
                        ]
                    }
                    
                    if enable_asd:
                        payload["options"] = {
                            "active_speaker_detection": {"auto_detect": True}
                        }
                    
                    response = requests.post(api_endpoint, headers=headers, json=payload, timeout=30)
                    response.raise_for_status()
                    result = response.json()
                    job_id = result.get("id")
                    
                    return (idx, job_id, "submitted", None)
                except Exception as e:
                    return (idx, None, f"failed:{str(e)}", None)
            
            # Submit jobs in parallel
            with ThreadPoolExecutor(max_workers=max_workers) as ex:
                futures = {ex.submit(submit_job, i): i for i in all_indices}
                
                for fut in as_completed(futures):
                    idx = futures[fut]
                    try:
                        job_idx, job_id, status, error = fut.result()
                        results.append({
                            "index": job_idx,
                            "job_id": job_id,
                            "status": status,
                            "error": error
                        })
                        if job_id:
                            job_ids[job_idx] = job_id
                    except Exception as e:
                        results.append({
                            "index": idx,
                            "job_id": None,
                            "status": f"failed:{str(e)}",
                            "error": str(e)
                        })
            
            # Monitor and download outputs if requested
            if download_outputs and s3_client and s3_output_base:
                completed_downloads = []
                
                def download_job_output(job_idx: int, job_id: str) -> tuple:
                    try:
                        job_s3_path = f"{s3_output_base.rstrip('/')}/{job_id}/"
                        
                        # List files in job folder
                        bucket = s3_output_base.replace('s3://', '').split('/')[0]
                        prefix = f"{s3_output_base.replace('s3://', '').split('/', 1)[1]}/{job_id}/"
                        
                        paginator = s3_client.get_paginator('list_objects_v2')
                        pages = paginator.paginate(Bucket=bucket, Prefix=prefix)
                        
                        output_file = None
                        for page in pages:
                            if 'Contents' not in page:
                                continue
                            for obj in page['Contents']:
                                key = obj['Key']
                                if key.endswith('.mp4'):
                                    output_file = key
                                    break
                            if output_file:
                                break
                        
                        if not output_file:
                            return (job_idx, job_id, "no_output_found", None)
                        
                        # Download file
                        local_job_dir = output_dir / job_id
                        local_job_dir.mkdir(parents=True, exist_ok=True)
                        
                        local_file = local_job_dir / Path(output_file).name
                        s3_client.download_file(bucket, output_file, str(local_file))
                        
                        return (job_idx, job_id, "downloaded", str(local_file))
                    except Exception as e:
                        return (job_idx, job_id, f"download_failed:{str(e)}", None)
                
                # Monitor until all outputs are available
                max_wait_time = 3600 * 2  # 2 hours max
                start_time = time.time()
                
                while time.time() - start_time < max_wait_time:
                    
                    if not pending:
                        break
                    
                    # Try downloading pending jobs
                    for result in pending:
                        job_idx = result["index"]
                        
                        job_idx_check, job_id_check, status, local_path = download_job_output(job_idx, job_id)
                        if status == "downloaded":
                            result["local_path"] = local_path
                            completed_downloads.append(local_path)
                    
                    # Check if all done
                    if all(r["status"] in ["completed", "failed"] for r in results if r.get("job_id")):
                        break
                    
                    time.sleep(monitor_interval)
            
            # Collect all downloaded files
            output_files = []
            for result in results:
                if result.get("local_path"):
                    output_files.append(normalize_path(result["local_path"]))
            
            # Also scan output directory for any files
            if output_dir.exists():
                output_files.extend([f for f in output_dir.rglob("*.mp4") if f.is_file()])
            
            # Return DIRECTORY_DATA structure
            directory_data = {
                "path": ensure_absolute_path(output_dir),
                "file_count": len(output_files),
                "files": [ensure_absolute_path(f) for f in output_files],
            }
            
            completed_count = sum(1 for r in results if r["status"] == "completed")
            results_json = json.dumps(results, indent=2)
            job_ids_json = json.dumps(job_ids, indent=2)
            
            return (
                completed_count,
                directory_data,
                results_json,
                job_ids_json
            )
            
        except Exception as e:
            return (0, {"error": format_error(e)}, "", "")
