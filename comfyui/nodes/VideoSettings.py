"""
ComfyUI node for configuring video/audio encoding settings.
These settings can be passed through the workflow to processing nodes.
"""
import sys
from pathlib import Path
from typing import Dict, Any

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

format_error = _comfyui_utils.format_error


class VideoSettings:
    """Configure video and audio encoding settings"""
    
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {},
            "optional": {
                "video_codec": (["prores", "h264", "h265", "dnxhd", "copy"], {"default": "prores"}),
                "video_profile": ("STRING", {"default": ""}),  # e.g., "422", "422HQ", "LT"
                "fps": ("FLOAT", {"default": 23.976, "min": 1.0, "max": 120.0, "step": 0.001}),
                "resolution_width": ("INT", {"default": 1920, "min": 1, "max": 7680}),
                "resolution_height": ("INT", {"default": 1080, "min": 1, "max": 4320}),
                "audio_codec": (["pcm", "aac", "mp3", "copy"], {"default": "pcm"}),
                "audio_bit_depth": (["16", "24", "32"], {"default": "24"}),
                "audio_sample_rate": (["44100", "48000", "96000"], {"default": "48000"}),
                "audio_channels": (["1", "2", "5.1", "7.1"], {"default": "2"}),
            }
        }
    
    RETURN_TYPES = ("VIDEO_SETTINGS",)
    RETURN_NAMES = ("settings",)
    FUNCTION = "run"
    CATEGORY = "sync-toolkit/config"
    
    def run(self, video_codec: str = "prores", video_profile: str = "",
            fps: float = 23.976, resolution_width: int = 1920, resolution_height: int = 1080,
            audio_codec: str = "pcm", audio_bit_depth: str = "24",
            audio_sample_rate: str = "48000", audio_channels: str = "2"):
        """Create settings object"""
        try:
            settings = {
                "video": {
                    "codec": video_codec,
                    "profile": video_profile,
                    "fps": fps,
                    "width": resolution_width,
                    "height": resolution_height,
                },
                "audio": {
                    "codec": audio_codec,
                    "bit_depth": int(audio_bit_depth),
                    "sample_rate": int(audio_sample_rate),
                    "channels": audio_channels,
                }
            }
            
            return (settings,)
            
        except Exception as e:
            return ({"error": format_error(e)},)

