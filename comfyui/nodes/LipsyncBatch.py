"""
ComfyUI node for batch lipsync processing.
Wraps scripts/api/lipsync_batch.py
"""
import sys
import json
from pathlib import Path

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

# Import utils - use absolute import from current directory
# Add current directory (comfyui) to path FIRST for utils import
COMFYUI_DIR = Path(__file__).parent.parent.resolve()
if str(COMFYUI_DIR) not in sys.path:
    sys.path.insert(0, str(COMFYUI_DIR))

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


class LipsyncBatch:
    """Run batch lipsync processing from manifest file"""
    
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "manifest_path": ("STRING", {"default": ""}),
            },
            "optional": {
                "credentials": ("CREDENTIALS", {"default": None}),
                "start_index": ("INT", {"default": 1, "min": 1}),
                "end_index": ("INT", {"default": 0, "min": 0}),  # 0 means use default
                "max_workers": ("INT", {"default": 15, "min": 1, "max": 15}),
                "check_exists": ("BOOLEAN", {"default": True}),
                "keep_asd": ("BOOLEAN", {"default": False}),
            }
        }
    
    RETURN_TYPES = ("INT", "STRING", "STRING", "STRING")
    RETURN_NAMES = ("completed_count", "output_directory", "results_json", "manifest_path")
    FUNCTION = "run"
    CATEGORY = "sync-toolkit/api"
    
    def run(self, manifest_path: str, credentials: dict = None,
            start_index: int = 1, end_index: int = 0,
            max_workers: int = 15, check_exists: bool = True,
            keep_asd: bool = False):
        """Run batch processing"""
        try:
            # Extract credentials
            creds = credentials or {}
            api_key = creds.get("sync_api_key", "") or get_sync_api_key("")
            if not api_key:
                return (0, "", "", "ERROR: Sync API key required")
            
            # Normalize manifest path
            manifest_file = normalize_path(manifest_path)
            if not manifest_file.exists():
                return (0, "", "", "ERROR: Manifest file not found")
            
            # Import batch processing functions
            from api.lipsync_batch import (
                parse_manifest, process_index, OUTDIR
            )
            from concurrent.futures import ThreadPoolExecutor, as_completed
            import logging
            
            # Parse manifest
            video_urls, audio_urls = parse_manifest(manifest_file)
            if not video_urls or not audio_urls:
                return (0, "", "", "ERROR: No video/audio URLs found in manifest")
            
            # Set end index
            if end_index == 0:
                end_index = min(len(video_urls), len(audio_urls))
            
            # Clamp indices
            max_pairs = min(len(video_urls), len(audio_urls))
            end_idx = min(end_index, max_pairs)
            
            if start_index < 1 or end_idx < start_index:
                return (0, "", "", "ERROR: Invalid start/end range")
            
            # Clamp workers
            workers = max(1, min(max_workers, 15))
            
            # Create output directory
            OUTDIR.mkdir(exist_ok=True)
            
            # Process indices
            all_indices = list(range(start_index, end_idx + 1))
            completed = []
            results = []
            
            with ThreadPoolExecutor(max_workers=workers) as ex:
                futures = {
                    ex.submit(
                        process_index,
                        idx=i,
                        api_key=api_key,
                        video_urls=video_urls,
                        audio_urls=audio_urls,
                        check_exists=check_exists,
                        force_asd=keep_asd,
                    ): i for i in all_indices
                }
                
                for fut in as_completed(futures):
                    idx = futures[fut]
                    try:
                        i, status = fut.result()
                        results.append({"index": i, "status": status})
                        if status == "completed":
                            completed.append(i)
                    except Exception as e:
                        results.append({"index": idx, "status": f"failed:{e}"})
            
            # Save results JSON
            results_file = OUTDIR / "batch_results.json"
            with open(results_file, 'w') as f:
                json.dump(results, f, indent=2)
            
            return (
                len(completed),
                ensure_absolute_path(OUTDIR),
                json.dumps(results),
                ensure_absolute_path(manifest_file)
            )
            
        except Exception as e:
            return (0, "", "", format_error(e))

