"""
ComfyUI node for preparing batch lipsync requests.
Creates request payloads but does not execute API calls.
Actual API execution is handled by SyncDevAPI or SyncCustomEndpoint nodes.
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

# Import utils from comfyui directory using importlib to avoid conflict with scripts/utils
import importlib.util
utils_path = COMFYUI_DIR / "utils.py"
utils_spec = importlib.util.spec_from_file_location("comfyui_utils", utils_path)
_comfyui_utils = importlib.util.module_from_spec(utils_spec)
utils_spec.loader.exec_module(_comfyui_utils)

normalize_path = _comfyui_utils.normalize_path
ensure_absolute_path = _comfyui_utils.ensure_absolute_path
format_error = _comfyui_utils.format_error


class LipsyncBatch:
    """Prepare batch lipsync requests from manifest file"""
    
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "manifest_path": ("STRING", {"default": ""}),
            },
            "optional": {
                "start_index": ("INT", {"default": 1, "min": 1}),
                "end_index": ("INT", {"default": 0, "min": 0}),  # 0 means process all
                "enable_asd": ("BOOLEAN", {"default": True}),
                "check_exists": ("BOOLEAN", {"default": False}),  # Check if URLs exist before creating requests
        }
    
    RETURN_TYPES = ("STRING", "STRING", "INT")
    RETURN_NAMES = ("requests_json", "manifest_path", "request_count")
    FUNCTION = "run"
    CATEGORY = "sync-toolkit/api"
    
    def run(self, manifest_path: str, start_index: int = 1, end_index: int = 0,
            enable_asd: bool = True, check_exists: bool = False):
        """Prepare batch requests from manifest"""
        try:
            # Normalize manifest path
            manifest_file = normalize_path(manifest_path)
            if not manifest_file.exists():
                return ("", "", 0)
            
            # Parse manifest
            from utils.common import parse_manifest
            video_urls, audio_urls = parse_manifest(manifest_file)
            
            if not video_urls or not audio_urls:
                return ("", "", 0)
            
            # Set end index (0 means process all)
            if end_index == 0:
                end_index = min(len(video_urls), len(audio_urls))
            
            # Clamp indices
            max_pairs = min(len(video_urls), len(audio_urls))
            end_idx = min(end_index, max_pairs)
            
            if start_index < 1 or end_idx < start_index:
                return ("", "", 0)
            
            # Create request payloads
            all_indices = list(range(start_index, end_idx + 1))
            requests = []
            
            for idx in all_indices:
                vid_url = video_urls[idx - 1]
                aud_url = audio_urls[idx - 1]
                
                # Optionally check if URLs exist
                if check_exists:
                    try:
                        import requests as req_lib
                        vid_resp = req_lib.head(vid_url, timeout=10, allow_redirects=True)
                        aud_resp = req_lib.head(aud_url, timeout=10, allow_redirects=True)
                        if vid_resp.status_code != 200 or aud_resp.status_code != 200:
                            continue  # Skip invalid URLs
                    except Exception:
                        continue  # Skip if check fails
                
                # Build request payload
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
                
                requests.append({
                    "index": idx,
                    "video_url": vid_url,
                    "audio_url": aud_url,
                    "payload": payload
                })
            
            # Return requests as JSON string
            requests_json = json.dumps(requests, indent=2)
            
            return (
                requests_json,
                ensure_absolute_path(manifest_file),
                len(requests)
            )
            
        except Exception as e:
            return ("", "", 0)
