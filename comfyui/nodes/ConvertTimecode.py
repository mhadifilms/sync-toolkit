"""
ComfyUI node for converting timecodes between frame rates.
Wraps scripts/utils/timecode.py
"""
import sys
import csv
from pathlib import Path

# Add current directory (comfyui) to path for utils import
COMFYUI_DIR = Path(__file__).parent.parent
if str(COMFYUI_DIR) not in sys.path:

# Add project root to path
PROJECT_ROOT = COMFYUI_DIR.parent
if str(PROJECT_ROOT) not in sys.path:

# Add scripts directory to path
SCRIPT_DIR = PROJECT_ROOT / "scripts"
if str(SCRIPT_DIR) not in sys.path:

# Import utils - use absolute import from current directory
# Add current directory (comfyui) to path FIRST for utils import
COMFYUI_DIR = Path(__file__).parent.parent.resolve()
if str(COMFYUI_DIR) not in sys.path:

# Import utils from comfyui directory using importlib to avoid conflict with scripts/utils
import importlib.util
utils_path = COMFYUI_DIR / "utils.py"
utils_spec = importlib.util.spec_from_file_location("comfyui_utils", utils_path)
_comfyui_utils = importlib.util.module_from_spec(utils_spec)
utils_spec.loader.exec_module(_comfyui_utils)

normalize_path = _comfyui_utils.normalize_path
ensure_absolute_path = _comfyui_utils.ensure_absolute_path
format_error = _comfyui_utils.format_error


class ConvertTimecode:
    
    @classmethod
    def INPUT_TYPES(cls):
            "required": {
                "input_type": (["single", "csv"], {"default": "single"}),
                "source_fps": ("STRING", {"default": "24"}),
                "target_fps": ("STRING", {"default": "23.976"}),
            },
            "optional": {
                "directory_data": ("DIRECTORY_DATA", {"default": None}),
                "timecode": ("STRING", {"default": ""}),
                "csv_path": ("STRING", {"default": ""}),  # Legacy support
                "start_column": ("STRING", {"default": "Event Start Time"}),
                "end_column": ("STRING", {"default": "Event End Time"}),
                "duration_column": ("STRING", {"default": "Event Duration"}),
        }
    
    RETURN_TYPES = ("STRING", "INT")
    RETURN_NAMES = ("output", "conversion_count")
    FUNCTION = "run"
    CATEGORY = "sync-toolkit/utility"
    
    def run(self, input_type: str, source_fps: str, target_fps: str,
            directory_data: dict = None, timecode: str = "", csv_path: str = "",
            start_column: str = "Event Start Time",
            end_column: str = "Event End Time",
            duration_column: str = "Event Duration"):
        """Run timecode conversion"""
        try:
                parse_fps, timecode_to_frames, frames_to_timecode
            )
            
            source_fps_val = parse_fps(source_fps)
            target_fps_val = parse_fps(target_fps)
            
            if input_type == "single":
                    return ("ERROR: Timecode required for single mode", 0)
                
                # Convert single timecode
                frames = timecode_to_frames(timecode, source_fps_val)
                converted_tc = frames_to_timecode(frames, target_fps_val)
                
                return (converted_tc, 1)
            
            else:  # csv mode
                # Extract CSV path from DIRECTORY_DATA or use legacy string input
                if directory_data and not directory_data.get("error"):
                    dir_path = normalize_path(directory_data.get("path", ""))
                    csv_files = list(dir_path.glob("*.csv"))
                    if csv_files:
                    else:
                elif csv_path:

                else:
                
                if not csv_file.exists():
                
                # Read CSV
                rows = []
                with open(csv_file, 'r', encoding='utf-8') as f:
                    rows = list(reader)
                
                if not rows:
                
                # Convert timecodes in CSV
                converted_count = 0
                for row in rows:
                    if start_column in row and row[start_column]:
                            frames = timecode_to_frames(row[start_column], source_fps_val)
                            row[start_column] = frames_to_timecode(frames, target_fps_val)
                            converted_count += 1
                        except Exception:
                    
                    # Convert end timecode
                    if end_column in row and row[end_column]:
                            frames = timecode_to_frames(row[end_column], source_fps_val)
                            row[end_column] = frames_to_timecode(frames, target_fps_val)
                            converted_count += 1
                        except Exception:
                    
                    # Convert duration if present
                    if duration_column in row and row[duration_column]:
                            # Duration might be in frames or timecode format
                            if ':' in row[duration_column]:
                                row[duration_column] = frames_to_timecode(frames, target_fps_val)
                            else:
                                frames = int(row[duration_column])
                                # Convert frame count
                                source_duration_sec = frames / source_fps_val
                                target_frames = int(source_duration_sec * target_fps_val)
                                row[duration_column] = str(target_frames)
                            converted_count += 1
                        except Exception:
                
                # Write output CSV
                output_file = csv_file.parent / f"{csv_file.stem}_converted{csv_file.suffix}"
                with open(output_file, 'w', encoding='utf-8', newline='') as f:
                        writer = csv.DictWriter(f, fieldnames=rows[0].keys())
                        writer.writeheader()
                        writer.writerows(rows)
                
                return (ensure_absolute_path(output_file), converted_count)
            
        except Exception as e:

