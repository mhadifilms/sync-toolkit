"""
ComfyUI node for detecting and splitting video scenes.
Wraps scripts/video/detect_scenes.py
"""
import sys
from pathlib import Path

# Add current directory (comfyui) to path FIRST for utils import
COMFYUI_DIR = Path(__file__).parent.parent.resolve()
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


class DetectScenes:
    """Detect scene boundaries and split video/audio into segments"""
    
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {},
            "optional": {
                "video_data": ("VIDEO_DATA", {"default": None}),
                "audio_data": ("AUDIO_DATA", {"default": None}),
                "video_path": ("STRING", {"default": ""}),  # Legacy support
                "audio_path": ("STRING", {"default": ""}),  # Legacy support
                "output_dir": ("STRING", {"default": ""}),
            }
        }
    
    RETURN_TYPES = ("DIRECTORY_DATA", "STRING", "INT")
    RETURN_NAMES = ("output_directory", "csv_path", "segment_count")
    FUNCTION = "run"
    CATEGORY = "sync-toolkit/video"
    
    def run(self, video_data: dict = None, audio_data: dict = None,
            video_path: str = "", audio_path: str = "", output_dir: str = ""):
        """Run scene detection"""
        try:
            from video.detect_scenes import (
                need, ffprobe_duration, detect_cuts_ffmpeg,
                detect_cuts_pyscenedetect, coalesce, build_segments,
                write_csv, split_video_copy, probe_audio_pcm, split_audio_pcm
            )
            
            # Extract video path from VIDEO_DATA or use legacy string input
            video_in = None
            if video_data and not video_data.get("error"):
                video_in = normalize_path(video_data.get("primary_file", ""))
            elif video_path:
                video_in = normalize_path(video_path)
            else:
                return ({"error": "ERROR: Video path required"}, "", 0)
            
            if not video_in.exists():
                return ({"error": "ERROR: Video file not found"}, "", 0)
            
            # Extract audio path from AUDIO_DATA or use legacy string input
            audio_in = None
            if audio_data and not audio_data.get("error"):
                audio_in = normalize_path(audio_data.get("primary_file", ""))
            elif audio_path:
                audio_in = normalize_path(audio_path)
            
            # Set output directory
            if output_dir:
                out_dir = normalize_path(output_dir)
            else:
                out_dir = video_in.parent / "Scenes"
            out_dir.mkdir(parents=True, exist_ok=True)
            
            # Check for required tools
            need("ffmpeg")
            need("ffprobe")
            
            # Get video duration
            duration = ffprobe_duration(str(video_in))
            
            # Detect cuts
            PSD_THRESHOLD = 22.0
            PSD_MIN_FRAMES = 8
            FFMPEG_SCENE = 0.30
            MIN_GAP_SEC = 0.33
            
            cuts_psd = detect_cuts_pyscenedetect(str(video_in), PSD_THRESHOLD, PSD_MIN_FRAMES)
            cuts_ff = detect_cuts_ffmpeg(str(video_in), FFMPEG_SCENE)
            
            merged = sorted(set([*cuts_psd, *cuts_ff]))
            merged = coalesce(merged, MIN_GAP_SEC)
            
            segments = build_segments(duration, merged)
            if not segments:
                return ({"error": "ERROR: No segments found"}, "", 0)
            
            # Write CSV
            csv_path = out_dir / "scene_cuts.csv"
            write_csv(segments, csv_path)
            
            # Split video
            split_video_copy(str(video_in), segments, out_dir)
            
            # Split audio if provided
            if audio_in and audio_in.exists():
                pcm_codec = probe_audio_pcm(str(audio_in))
                split_audio_pcm(str(audio_in), segments, out_dir, pcm_codec)
            
            # Get all output files
            output_files = list(out_dir.glob("*.mov")) + list(out_dir.glob("*.wav"))
            
            # Return DIRECTORY_DATA structure
            directory_data = {
                "path": ensure_absolute_path(out_dir),
                "file_count": len(output_files),
                "files": [ensure_absolute_path(f) for f in output_files],
            }
            
            return (
                directory_data,
                ensure_absolute_path(csv_path),
                len(segments)
            )
            
        except Exception as e:
            return ({"error": format_error(e)}, "", 0)
