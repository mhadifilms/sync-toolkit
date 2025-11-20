#!/usr/bin/env python3
"""
Common utilities for Sync Toolkit scripts.
"""
import os
import sys
import json
import mimetypes
from pathlib import Path
from typing import List, Tuple, Optional, Dict, Any, Union
import re


def normalize_path(path: Union[str, Path]) -> Path:
    """Normalize a path, handling drag-and-drop formats"""
    if isinstance(path, str):
        # Handle backslash-escaped spaces (Finder → Terminal)
        path = path.replace('\\ ', ' ')
        # Handle quoted paths
        if (path.startswith('"') and path.endswith('"')) or \
           (path.startswith("'") and path.endswith("'")):
            path = path[1:-1]
        # Remove trailing slashes
        if len(path) > 1 and path.endswith('/'):
            path = path[:-1]
    
    return Path(path).expanduser().resolve()


def prompt_path(prompt: str, must_exist: bool = True, default: Optional[str] = None) -> Path:
    """Prompt user for a file or directory path"""
    while True:
        if default:
            user_input = input(f"{prompt} [{default}]: ").strip()
            if not user_input:
                user_input = default
        else:
            user_input = input(f"{prompt}: ").strip()
        
        if not user_input:
            print("Path cannot be empty.")
            continue
        
        path = normalize_path(user_input)
        
        if must_exist and not path.exists():
            print(f"Path does not exist: {path}")
            continue
        
        return path


def prompt_choice(prompt: str, choices: List[str], default: Optional[str] = None) -> str:
    """Prompt user to choose from a list of options"""
    print(f"\n{prompt}")
    for i, choice in enumerate(choices, 1):
        marker = " (default)" if choice == default else ""
        print(f"  {i}. {choice}{marker}")
    
    while True:
        user_input = input("Enter choice: ").strip()
        
        if not user_input and default:
            return default
        
        try:
            idx = int(user_input) - 1
            if 0 <= idx < len(choices):
                return choices[idx]
        except ValueError:
            pass
        
        # Try direct match
        if user_input in choices:
            return user_input
        
        print(f"Invalid choice. Please enter 1-{len(choices)} or the option name.")


def parse_manifest(manifest_path: Path) -> Tuple[List[str], List[str]]:
    """Parse uploaded_urls.txt manifest into video and audio URL lists"""
    videos: List[str] = []
    audios: List[str] = []
    
    if not manifest_path.exists():
        raise FileNotFoundError(f"Manifest not found: {manifest_path}")
    
    mode: Optional[str] = None
    with open(manifest_path, "r", encoding="utf-8") as f:
        for raw in f:
            line = raw.strip()
            if not line:
                continue
            
            upper = line.upper()
            if upper == "VIDEOS":
                mode = "v"
                continue
            if upper == "AUDIOS":
                mode = "a"
                continue
            
            if mode == "v":
                name = line.rsplit('/', 1)[-1]
                if not name.startswith("._"):
                    videos.append(line)
            elif mode == "a":
                name = line.rsplit('/', 1)[-1]
                if not name.startswith("._"):
                    audios.append(line)
    
    # De-duplicate while preserving order
    def dedup(seq: List[str]) -> List[str]:
        seen: Dict[str, bool] = {}
        out: List[str] = []
        for s in seq:
            if s in seen:
                continue
            seen[s] = True
            out.append(s)
        return out
    
    videos = dedup(videos)
    audios = dedup(audios)
    return videos, audios


def write_manifest(video_urls: List[str], audio_urls: List[str], output_path: Path):
    """Write a manifest file in VIDEOS/AUDIOS format"""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("VIDEOS\n")
        for url in video_urls:
            f.write(url + "\n")
        f.write("\nAUDIOS\n")
        for url in audio_urls:
            f.write(url + "\n")


def guess_mime_type(path: Path) -> str:
    """Guess MIME type for a file"""
    mime, _ = mimetypes.guess_type(str(path))
    return mime or 'application/octet-stream'


def is_video_file(path: Path) -> bool:
    """Check if file is a video"""
    mime = guess_mime_type(path)
    return mime.startswith('video/')


def is_audio_file(path: Path) -> bool:
    """Check if file is an audio"""
    mime = guess_mime_type(path)
    return mime.startswith('audio/')


def find_media_files(directory: Path, video_exts: Optional[List[str]] = None, 
                     audio_exts: Optional[List[str]] = None) -> Tuple[List[Path], List[Path]]:
    """Find video and audio files in a directory"""
    if video_exts is None:
        video_exts = ['.mov', '.mp4', '.avi', '.mkv', '.m4v']
    if audio_exts is None:
        audio_exts = ['.wav', '.mp3', '.m4a', '.aac', '.flac']
    
    videos: List[Path] = []
    audios: List[Path] = []
    
    for ext in video_exts:
        videos.extend(directory.glob(f"*{ext}"))
        videos.extend(directory.glob(f"*{ext.upper()}"))
    
    for ext in audio_exts:
        audios.extend(directory.glob(f"*{ext}"))
        audios.extend(directory.glob(f"*{ext.upper()}"))
    
    # Remove duplicates and sort
    videos = sorted(set(videos))
    audios = sorted(set(audios))
    
    return videos, audios


def natural_sort_key(s: str) -> List[Union[int, str]]:
    """Generate a key for natural sorting (handles numbers correctly)"""
    return [int(t) if t.isdigit() else t.lower() for t in re.findall(r'\d+|\D+', s)]


def format_duration(seconds: float) -> str:
    """Format duration in seconds to HH:MM:SS.mmm"""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = seconds % 60
    return f"{hours:02d}:{minutes:02d}:{secs:06.3f}"


def print_section(title: str, width: int = 60):
    """Print a formatted section header"""
    print("\n" + "=" * width)
    if title:
        print(title)
        print("=" * width)
    else:
        print("=" * width)


def print_progress(current: int, total: int, prefix: str = "Progress"):
    """Print progress indicator"""
    percent = (current / total * 100) if total > 0 else 0
    bar_length = 40
    filled = int(bar_length * current / total) if total > 0 else 0
    bar = "█" * filled + "░" * (bar_length - filled)
    print(f"\r{prefix}: [{bar}] {current}/{total} ({percent:.1f}%)", end="", flush=True)
    if current == total:
        print()  # New line when complete


def save_json(data: Any, path: Path, indent: int = 2):
    """Save data as JSON file"""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=indent, ensure_ascii=False)


def load_json(path: Path) -> Any:
    """Load JSON file"""
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def ensure_output_dir(path: Path) -> Path:
    """Ensure output directory exists and return it"""
    path.mkdir(parents=True, exist_ok=True)
    return path


def slugify(name: str) -> str:
    """Convert a name to a URL-safe slug"""
    name = name.strip().replace(' ', '_')
    return re.sub(r'[^A-Za-z0-9_\-]+', '-', name)

