"""
ComfyUI Custom Nodes for Sync Toolkit

This package provides ComfyUI nodes that wrap sync-toolkit functions
for node-based workflow processing.
"""
import sys
import os
from pathlib import Path

# Ensure we can import from nodes directory
_current_file = Path(__file__).resolve()
_current_dir = _current_file.parent
if str(_current_dir) not in sys.path:
    sys.path.insert(0, str(_current_dir))

# Import nodes - try relative first, fallback to absolute
try:
    from .nodes import (
        DetectScenes,
        CreateShots,
        GroupByFace,
        ExtractAudio,
        BounceVideo,
        ChunkVideo,
        UploadToStorage,
        S3Download,
        S3Monitor,
        LipsyncBatch,
        ProcessCSV,
        ConvertTimecode,
        RenameFiles,
        LoadVideo,
        LoadAudio,
        VideoSettings,
        Credentials,
        MergeDirectories,
        FilterFiles,
        OrganizeOutputs,
        SyncDevAPI,
        SyncCustomEndpoint,
    )
except ImportError:
    # Fallback to absolute imports
    from nodes.DetectScenes import DetectScenes
    from nodes.CreateShots import CreateShots
    from nodes.GroupByFace import GroupByFace
    from nodes.ExtractAudio import ExtractAudio
    from nodes.BounceVideo import BounceVideo
    from nodes.ChunkVideo import ChunkVideo
    from nodes.UploadToStorage import UploadToStorage
    from nodes.S3Download import S3Download
    from nodes.S3Monitor import S3Monitor
    from nodes.LipsyncBatch import LipsyncBatch
    from nodes.ProcessCSV import ProcessCSV
    from nodes.ConvertTimecode import ConvertTimecode
    from nodes.RenameFiles import RenameFiles
    from nodes.LoadVideo import LoadVideo
    from nodes.LoadAudio import LoadAudio
    from nodes.VideoSettings import VideoSettings
    from nodes.Credentials import Credentials
    from nodes.MergeDirectories import MergeDirectories
    from nodes.FilterFiles import FilterFiles
    from nodes.OrganizeOutputs import OrganizeOutputs
    from nodes.SyncDevAPI import SyncDevAPI
    from nodes.SyncCustomEndpoint import SyncCustomEndpoint

# Export all node classes for ComfyUI
NODE_CLASS_MAPPINGS = {
    "DetectScenes": DetectScenes,
    "CreateShots": CreateShots,
    "GroupByFace": GroupByFace,
    "ExtractAudio": ExtractAudio,
    "BounceVideo": BounceVideo,
    "ChunkVideo": ChunkVideo,
    "UploadToStorage": UploadToStorage,
    "S3Download": S3Download,
    "S3Monitor": S3Monitor,
    "LipsyncBatch": LipsyncBatch,
    "ProcessCSV": ProcessCSV,
    "ConvertTimecode": ConvertTimecode,
    "RenameFiles": RenameFiles,
    "LoadVideo": LoadVideo,
    "LoadAudio": LoadAudio,
    "VideoSettings": VideoSettings,
    "Credentials": Credentials,
    "MergeDirectories": MergeDirectories,
    "FilterFiles": FilterFiles,
    "OrganizeOutputs": OrganizeOutputs,
    "SyncDevAPI": SyncDevAPI,
    "SyncCustomEndpoint": SyncCustomEndpoint,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "DetectScenes": "Detect Scenes",
    "CreateShots": "Create Shots",
    "GroupByFace": "Group By Face",
    "ExtractAudio": "Extract Audio",
    "BounceVideo": "Bounce Video",
    "ChunkVideo": "Chunk Video",
    "UploadToStorage": "Upload To Storage",
    "S3Download": "S3 Download",
    "S3Monitor": "S3 Monitor",
    "LipsyncBatch": "Lipsync Batch",
    "ProcessCSV": "Process CSV",
    "ConvertTimecode": "Convert Timecode",
    "RenameFiles": "Rename Files",
    "LoadVideo": "Load Video",
    "LoadAudio": "Load Audio",
    "VideoSettings": "Video Settings",
    "Credentials": "Credentials",
    "MergeDirectories": "Merge Directories",
    "FilterFiles": "Filter Files",
    "OrganizeOutputs": "Organize Outputs",
    "SyncDevAPI": "Sync Dev API",
    "SyncCustomEndpoint": "Sync Custom Endpoint",
}

__all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS"]

