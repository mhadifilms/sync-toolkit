"""
ComfyUI node for creating video shots from CSV.
Wraps scripts/video/create_shots.py
"""
import sys
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


class CreateShots:
    """Create individual video shots from CSV spotting data"""
    
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "csv_path": ("STRING", {"default": ""}),
            },
            "optional": {
                "video_data": ("VIDEO_DATA", {"default": None}),
                "video_path": ("STRING", {"default": ""}),  # Legacy support
                "output_dir": ("STRING", {"default": ""}),
            }
        }
    
    RETURN_TYPES = ("DIRECTORY_DATA", "INT")
    RETURN_NAMES = ("output_directory", "clips_count")
    FUNCTION = "run"
    CATEGORY = "sync-toolkit/video"
    
    def run(self, csv_path: str, video_data: dict = None, video_path: str = "", output_dir: str = ""):
        """Run shot creation"""
        try:
            from video.create_shots import cut_videos_directly
            import csv
            from utils.timecode import tc24_to_frames
            
            # Extract video path from VIDEO_DATA or use legacy string input
            if video_data and not video_data.get("error"):
                video_in = normalize_path(video_data.get("primary_file", ""))
            elif video_path:
                video_in = normalize_path(video_path)
            else:
                return ({"error": "ERROR: Video path required"}, 0)
            
            csv_in = normalize_path(csv_path)
            
            if not video_in.exists():
                return ("ERROR: Video file not found", 0)
            if not csv_in.exists():
                return ("ERROR: CSV file not found", 0)
            
            # Set output directory
            if output_dir:
                out_dir = normalize_path(output_dir)
            else:
                out_dir = video_in.parent / "vub_clips_23976"
            out_dir.mkdir(parents=True, exist_ok=True)
            
            # Read CSV
            with csv_in.open("r", newline="", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                raw_rows = list(reader)
            
            # Filter rows that have start/end timecodes
            rows = []
            for row in raw_rows:
                start_tc = (row.get("Event Start Time") or "").strip()
                end_tc = (row.get("Event End Time") or "").strip()
                if start_tc and end_tc:
                    rows.append(row)
            
            if not rows:
                return ("ERROR: No usable rows found with Event Start Time / Event End Time", 0)
            
            # Sort by start time
            def sort_key(row):
                try:
                    return tc24_to_frames((row.get("Event Start Time") or "").strip())
                except ValueError:
                    return 0
            rows.sort(key=sort_key)
            
            # Create mock args object
            class MockArgs:
                show_id = "SHOW001"
                limit = None
            
            args = MockArgs()
            
            # Call cut_videos_directly
            cut_videos_directly(args, video_in, out_dir, rows)
            
            # Count created clips
            clips = list(out_dir.glob("*.mov"))
            clips_count = len(clips)
            
            # Return DIRECTORY_DATA structure
            directory_data = {
                "path": ensure_absolute_path(out_dir),
                "file_count": clips_count,
                "files": [ensure_absolute_path(f) for f in clips],
            }
            
            return (directory_data, clips_count)
            
        except Exception as e:
            return ({"error": format_error(e)}, 0)

