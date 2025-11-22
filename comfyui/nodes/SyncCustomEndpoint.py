"""
ComfyUI node for Sync.so Custom Endpoint processing.
Allows setting custom output folder in S3, monitors outputs, and downloads them.
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


class SyncCustomEndpoint:
    """Process videos through Sync.so Custom Endpoint with configurable output folder"""
    
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "manifest_path": ("STRING", {"default": ""}),
                "custom_output_folder": ("STRING", {"default": ""}),  # S3 folder path for outputs
            },
            "optional": {
                "credentials": ("CREDENTIALS", {"default": None}),
                "api_endpoint": ("STRING", {"default": "https://api.sync.so/v2/generate"}),
                "output_base_dir": ("STRING", {"default": ""}),  # Local directory for downloads
                "start_index": ("INT", {"default": 1, "min": 1}),
                "end_index": ("INT", {"default": 0, "min": 0}),  # 0 means process all
                "max_workers": ("INT", {"default": 15, "min": 1, "max": 15}),
                "enable_asd": ("BOOLEAN", {"default": True}),
                "monitor_interval": ("INT", {"default": 180, "min": 10}),  # Seconds between S3 checks
                "download_outputs": ("BOOLEAN", {"default": True}),  # Download completed outputs
                "preserve_names": ("BOOLEAN", {"default": True}),  # Keep same names as input
            }
        }
    
    RETURN_TYPES = ("INT", "DIRECTORY_DATA", "STRING", "STRING")
    RETURN_NAMES = ("completed_count", "output_directory", "results_json", "output_urls_json")
    FUNCTION = "run"
    CATEGORY = "sync-toolkit/api"
    
    def run(self, manifest_path: str, custom_output_folder: str,
            credentials: dict = None,
            api_endpoint: str = "https://api.sync.so/v2/generate",
            output_base_dir: str = "", start_index: int = 1, end_index: int = 0,
            max_workers: int = 15, enable_asd: bool = True,
            monitor_interval: int = 180, download_outputs: bool = True,
            preserve_names: bool = True):
        """Run custom endpoint processing"""
        try:
            creds = credentials or {}
            api_key = creds.get("sync_api_key", "") or get_sync_api_key("")
            if not api_key:
                return (0, {"error": "ERROR: Sync API key required"}, "", "")
            
            aws_access_key_id = creds.get("aws_access_key_id", "")
            aws_secret_key = creds.get("aws_secret_access_key", "")
            aws_region = creds.get("aws_region", "us-east-1")
            use_sso = creds.get("use_sso", False)
            
            if not custom_output_folder:
                return (0, {"error": "ERROR: Custom output folder required"}, "", "")
            
            # Ensure custom_output_folder is S3 path
            if not custom_output_folder.startswith('s3://'):
                custom_output_folder = f"s3://{custom_output_folder}"
            if not custom_output_folder.endswith('/'):
                custom_output_folder += '/'
            
            # Get S3 client for monitoring/downloading
            s3_client = None
            if download_outputs:
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
                output_dir = manifest_file.parent / "custom_endpoint_outputs"
            output_dir.mkdir(parents=True, exist_ok=True)
            
            # Process indices
            all_indices = list(range(start_index, end_idx + 1))
            results = []
            output_urls = {}
            
            # Submit all jobs
            headers = {
                "x-api-key": api_key,
                "Content-Type": "application/json"
            }
            
            def submit_job(idx: int) -> tuple:
                try:
                    aud_url = audio_urls[idx - 1]
                    
                    # Generate output filename (preserve input name if requested)
                    if preserve_names:
                        # Extract filename from video URL
                        from urllib.parse import urlparse
                        vid_path = Path(urlparse(vid_url).path)
                        output_filename = vid_path.stem + ".mp4"
                    else:
                        output_filename = f"output_{idx:02d}.mp4"
                    
                    output_url = f"{custom_output_folder}{output_filename}"
                    
                    payload = {
                        "model": "lipsync-2-pro",
                        "input": [
                            {"type": "video", "url": vid_url},
                            {"type": "audio", "url": aud_url}
                        ],
                        "output": {
                            "url": output_url
                        }
                    }
                    
                    if enable_asd:
                        payload["options"] = {
                            "active_speaker_detection": {"auto_detect": True}
                        }
                    
                    response = requests.post(api_endpoint, headers=headers, json=payload, timeout=30)
                    response.raise_for_status()
                    result = response.json()
                    job_id = result.get("id")
                    
                    return (idx, job_id, output_url, "submitted", None)
                except Exception as e:
                    return (idx, None, None, f"failed:{str(e)}", None)
            
            # Submit jobs in parallel
            with ThreadPoolExecutor(max_workers=max_workers) as ex:
                futures = {ex.submit(submit_job, i): i for i in all_indices}
                
                for fut in as_completed(futures):
                    idx = futures[fut]
                    try:
                        job_idx, job_id, output_url, status, error = fut.result()
                        results.append({
                            "index": job_idx,
                            "job_id": job_id,
                            "output_url": output_url,
                            "status": status,
                            "error": error
                        })
                        if output_url:
                            output_urls[job_idx] = output_url
                    except Exception as e:
                        results.append({
                            "index": idx,
                            "job_id": None,
                            "output_url": None,
                            "status": f"failed:{str(e)}",
                            "error": str(e)
                        })
            
            # Monitor and download outputs if requested
            if download_outputs and s3_client:
                completed_downloads = []
                
                def download_output(job_idx: int, output_url: str) -> tuple:
                    try:
                        if not output_url.startswith('s3://'):
                            return (job_idx, output_url, "invalid_s3_url", None)
                        
                        s3_path = output_url.replace('s3://', '')
                        parts = s3_path.split('/', 1)
                        bucket = parts[0]
                        key = parts[1] if len(parts) > 1 else ''
                        
                        # Check if file exists
                        try:
                            s3_client.head_object(Bucket=bucket, Key=key)
                        except Exception:
                            return (job_idx, output_url, "not_found", None)
                        
                        # Download file
                        local_filename = Path(key).name
                        local_file = output_dir / local_filename
                        s3_client.download_file(bucket, key, str(local_file))
                        
                        return (job_idx, output_url, "downloaded", str(local_file))
                    except Exception as e:
                        return (job_idx, output_url, f"download_failed:{str(e)}", None)
                
                # Monitor until all outputs are available
                max_wait_time = 3600 * 2  # 2 hours max
                start_time = time.time()
                
                while time.time() - start_time < max_wait_time:
                    pending = [r for r in results if r.get("output_url") and r["status"] == "submitted"]
                    
                    if not pending:
                        break
                    
                    # Try downloading pending outputs
                    for result in pending:
                        output_url = result["output_url"]
                        job_idx = result["index"]
                        
                        job_idx_check, url_check, status, local_path = download_output(job_idx, output_url)
                        if status == "downloaded":
                            result["status"] = "completed"
                            result["local_path"] = local_path
                            completed_downloads.append(local_path)
                    
                    # Check if all done
                    if all(r["status"] in ["completed", "failed"] for r in results if r.get("output_url")):
                        break
                    
                    time.sleep(monitor_interval)
            
            # Collect all downloaded files
            output_files = []
            for result in results:
                    output_files.append(normalize_path(result["local_path"]))
            
            # Also scan output directory for any files
            if output_dir.exists():
                output_files.extend([f for f in output_dir.glob("*.mp4") if f.is_file()])
            
            # Return DIRECTORY_DATA structure
            directory_data = {
                "path": ensure_absolute_path(output_dir),
                "file_count": len(output_files),
                "files": [ensure_absolute_path(f) for f in output_files],
            }
            
            completed_count = sum(1 for r in results if r["status"] == "completed")
            results_json = json.dumps(results, indent=2)
            output_urls_json = json.dumps(output_urls, indent=2)
            
            return (
                completed_count,
                directory_data,
                results_json,
                output_urls_json
            )
            
        except Exception as e:
            return (0, {"error": format_error(e)}, "", "")
