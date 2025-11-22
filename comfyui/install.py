#!/usr/bin/env python3
"""
Installation script for ComfyUI custom nodes.

Creates a symlink (or copy if symlink not supported) from ComfyUI's custom_nodes
directory to this comfyui directory for live updates.
"""
import os
import sys
import shutil
from pathlib import Path
from typing import Optional


def find_comfyui_directory() -> Optional[Path]:
    """Find ComfyUI installation directory"""
    # Common locations (including Mac app)
    possible_locations = [
        Path.home() / "Library" / "Application Support" / "ComfyUI",
        Path.home() / "Documents" / "ComfyUI",
        Path.home() / "ComfyUI",
        Path.home() / ".local" / "share" / "ComfyUI",
        Path("/opt/ComfyUI"),
        Path("/usr/local/ComfyUI"),
    ]
    
    # Check environment variable
    comfyui_env = os.getenv("COMFYUI_PATH")
    if comfyui_env:
        possible_locations.insert(0, Path(comfyui_env))
    
    for location in possible_locations:
        if location.exists() and (location / "custom_nodes").exists():
            return location
    
    return None


def install_nodes(comfyui_dir: Path, project_comfyui: Path, use_symlink: bool = True):
    """Install nodes by creating symlink or copying files"""
    custom_nodes_dir = comfyui_dir / "custom_nodes"
    target_dir = custom_nodes_dir / "sync_toolkit"  # Use underscore for Python import compatibility
    
    # Remove existing installation
    if target_dir.exists():
        if target_dir.is_symlink():
            print(f"Removing existing symlink: {target_dir}")
            target_dir.unlink()
        else:
            print(f"Removing existing directory: {target_dir}")
            shutil.rmtree(target_dir)
    
    # Create installation
    if use_symlink:
        try:
            print(f"Creating symlink: {target_dir} -> {project_comfyui}")
            target_dir.symlink_to(project_comfyui)
            print("✓ Symlink created successfully!")
            return True
        except OSError as e:
            print(f"Failed to create symlink: {e}")
            print("Falling back to copying files...")
            use_symlink = False
    
    if not use_symlink:
        print(f"Copying files: {project_comfyui} -> {target_dir}")
        shutil.copytree(project_comfyui, target_dir)
        print("✓ Files copied successfully!")
        return False
    
    return False


def main():
    """Main installation function"""
    # Get project comfyui directory
    script_dir = Path(__file__).parent.resolve()
    project_comfyui = script_dir
    
    print("=" * 60)
    print("ComfyUI Sync Toolkit Installation")
    print("=" * 60)
    print(f"Project directory: {project_comfyui}")
    print()
    
    # Find ComfyUI directory
    comfyui_dir = find_comfyui_directory()
    if not comfyui_dir:
        print("ERROR: Could not find ComfyUI installation directory.")
        print()
        print("Please set COMFYUI_PATH environment variable or install ComfyUI in one of:")
        print("  - ~/ComfyUI")
        print("  - ~/.local/share/ComfyUI")
        print("  - /opt/ComfyUI")
        print("  - /usr/local/ComfyUI")
        sys.exit(1)
    
    print(f"Found ComfyUI: {comfyui_dir}")
    print()
    
    # Install nodes
    use_symlink = True
    if len(sys.argv) > 1 and sys.argv[1] == "--copy":
        use_symlink = False
    
    installed_as_symlink = install_nodes(comfyui_dir, project_comfyui, use_symlink)
    
    print()
    print("=" * 60)
    if installed_as_symlink:
        print("Installation complete! Changes will be reflected immediately.")
    else:
        print("Installation complete! Run this script again to update files.")
    print("=" * 60)


if __name__ == "__main__":
    main()

