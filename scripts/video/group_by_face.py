#!/usr/bin/env python3
"""
Group video clips by detected faces and optionally organize them into folders.

Uses InsightFace with ArcFace model for maximum accuracy, and DBSCAN clustering
for robust grouping. Can also organize clips into folders based on groupings.
"""
import cv2
import numpy as np
import sys
import shutil
from pathlib import Path
from collections import defaultdict
import json
import argparse

# Add parent directory to path for utils
SCRIPT_DIR = Path(__file__).parent.parent.resolve()
sys.path.insert(0, str(SCRIPT_DIR))
from utils.common import print_section, ensure_output_dir

# Try InsightFace first (most accurate), then fallback to alternatives
try:
    import insightface
    from sklearn.cluster import DBSCAN
    USE_INSIGHTFACE = True
except ImportError:
    USE_INSIGHTFACE = False
    try:
        from deepface import DeepFace
        from sklearn.cluster import DBSCAN
        USE_DEEPFACE = True
    except ImportError:
        USE_DEEPFACE = False
        print("ERROR: Please install InsightFace or DeepFace:", file=sys.stderr)
        print("  pip install insightface scikit-learn", file=sys.stderr)
        print("  OR", file=sys.stderr)
        print("  pip install deepface scikit-learn", file=sys.stderr)
        sys.exit(1)


# Initialize InsightFace model (ArcFace - most accurate)
app = None
if USE_INSIGHTFACE:
    try:
        # Use BUFFALO_L model (most accurate) - will auto-download if needed
        app = insightface.app.FaceAnalysis(name='buffalo_l', providers=['CPUExecutionProvider'])
        app.prepare(ctx_id=0, det_size=(640, 640))
        print("✓ Loaded InsightFace with ArcFace model (BUFFALO_L)")
    except Exception as e:
        print(f"Warning: Could not load InsightFace model: {e}", file=sys.stderr)
        print("Falling back to alternative...", file=sys.stderr)
        USE_INSIGHTFACE = False
        app = None


def extract_frames_from_video(video_path, num_frames=10):
    """
    Extract frames from a video file.
    
    Args:
        video_path: Path to video file
        num_frames: Number of frames to extract (evenly spaced)
    
    Returns:
        List of frames (numpy arrays in BGR format for InsightFace)
    """
    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        return []
    
    frames = []
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    
    if total_frames == 0:
        cap.release()
        return []
    
    # Extract evenly spaced frames
    frame_indices = np.linspace(0, total_frames - 1, num_frames, dtype=int)
    
    for idx in frame_indices:
        cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
        ret, frame = cap.read()
        if ret:
            frames.append(frame)  # Keep BGR for InsightFace
    
    cap.release()
    return frames


def extract_face_encodings_insightface(video_path, num_frames=10):
    """
    Extract face encodings using InsightFace (ArcFace model) - most accurate.
    
    Args:
        video_path: Path to video file
        num_frames: Number of frames to sample from video
    
    Returns:
        List of face encodings (512-dimensional vectors)
    """
    global app
    if app is None:
        return []
    
    frames = extract_frames_from_video(video_path, num_frames)
    all_encodings = []
    
    for frame in frames:
        try:
            # Detect and encode faces using InsightFace
            faces = app.get(frame)
            
            for face in faces:
                # Get the embedding (512-dimensional for ArcFace)
                embedding = face.embedding
                all_encodings.append(embedding)
        except Exception as e:
            # Skip frames with errors
            continue
    
    return all_encodings


def extract_face_encodings_deepface(video_path, num_frames=10):
    """
    Extract face encodings using DeepFace (fallback).
    """
    frames = extract_frames_from_video(video_path, num_frames)
    all_encodings = []
    
    for frame in frames:
        try:
            result = DeepFace.represent(
                img_path=frame,
                model_name='ArcFace',  # Use ArcFace model for accuracy
                enforce_detection=False,
                detector_backend='retinaface'  # More accurate detector
            )
            
            if result and len(result) > 0:
                for face_data in result:
                    embedding = face_data['embedding']
                    all_encodings.append(np.array(embedding))
        except Exception as e:
            continue
    
    return all_encodings


def extract_face_encodings(video_path, num_frames=10):
    """Wrapper to use the appropriate face recognition method."""
    if USE_INSIGHTFACE:
        return extract_face_encodings_insightface(video_path, num_frames)
    elif USE_DEEPFACE:
        return extract_face_encodings_deepface(video_path, num_frames)
    else:
        return []


def cosine_distance(emb1, emb2):
    """Calculate cosine distance between two embeddings."""
    emb1 = np.array(emb1)
    emb2 = np.array(emb2)
    # Normalize
    emb1 = emb1 / (np.linalg.norm(emb1) + 1e-10)
    emb2 = emb2 / (np.linalg.norm(emb2) + 1e-10)
    return 1 - np.dot(emb1, emb2)


def group_clips_by_face_clustering(clip_paths, eps=0.35, min_samples=2, num_frames=10):
    """
    Group video clips using DBSCAN clustering for maximum accuracy.
    
    Args:
        clip_paths: List of paths to video clips
        eps: Maximum distance between samples in same cluster (lower = stricter)
        min_samples: Minimum samples in a cluster
        num_frames: Number of frames to sample from each video
    
    Returns:
        Dictionary mapping face_id to list of clip paths
    """
    print(f"Processing {len(clip_paths)} clips...")
    print(f"Using: {'InsightFace (ArcFace)' if USE_INSIGHTFACE else 'DeepFace (ArcFace)'}")
    print(f"Clustering: DBSCAN (eps={eps}, min_samples={min_samples})")
    print(f"Frames per clip: {num_frames}")
    print()
    
    # Step 1: Extract all face encodings from all clips
    clip_encodings = {}  # clip_path -> list of encodings
    clip_representatives = {}  # clip_path -> representative encoding
    
    for i, clip_path in enumerate(clip_paths, 1):
        clip_path = Path(clip_path)
        if not clip_path.exists():
            print(f"[{i}/{len(clip_paths)}] ⚠ Skipping (not found): {clip_path.name}")
            continue
        
        print(f"[{i}/{len(clip_paths)}] Processing: {clip_path.name}")
        
        try:
            encodings = extract_face_encodings(clip_path, num_frames)
            
            if not encodings:
                print(f"  ⊘ No faces detected")
                clip_encodings[str(clip_path)] = []
                continue
            
            clip_encodings[str(clip_path)] = encodings
            
            # Use centroid as representative
            representative = np.mean(encodings, axis=0)
            clip_representatives[str(clip_path)] = representative
            
            print(f"  ✓ Found {len(encodings)} face(s)")
            
        except Exception as e:
            print(f"  ✗ Error: {e}")
            clip_encodings[str(clip_path)] = []
    
    print("\n" + "=" * 60)
    print("Clustering faces...")
    print("=" * 60)
    
    # Step 2: Prepare data for clustering
    clip_paths_list = list(clip_representatives.keys())
    if not clip_paths_list:
        return {'no_face': [str(p) for p in clip_paths]}
    
    X = np.array([clip_representatives[cp] for cp in clip_paths_list])
    
    # Step 3: Apply DBSCAN clustering
    # Use cosine distance metric
    from sklearn.metrics.pairwise import cosine_distances
    distance_matrix = cosine_distances(X)
    
    # DBSCAN with precomputed distances
    clustering = DBSCAN(eps=eps, min_samples=min_samples, metric='precomputed')
    labels = clustering.fit_predict(distance_matrix)
    
    # Step 4: Group clips by cluster labels
    face_groups = defaultdict(list)
    noise_clips = []
    
    for clip_path, label in zip(clip_paths_list, labels):
        if label == -1:  # Noise/outlier - reassign to nearest cluster
            noise_clips.append(clip_path)
        else:
            group_id = f"face_{label + 1:03d}"
            face_groups[group_id].append(clip_path)
    
    # Reassign noise clips to nearest cluster
    if noise_clips and len(face_groups) > 0:
        print(f"\nReassigning {len(noise_clips)} noise clips to nearest clusters...")
        for noise_clip in noise_clips:
            noise_encoding = clip_representatives[noise_clip]
            best_group = None
            best_distance = float('inf')
            
            # Find nearest cluster centroid
            for group_id, group_clips in face_groups.items():
                if not group_clips:
                    continue
                # Compute group centroid
                group_encodings = [clip_representatives[cp] for cp in group_clips if cp in clip_representatives]
                if group_encodings:
                    centroid = np.mean(group_encodings, axis=0)
                    distance = cosine_distance(noise_encoding, centroid)
                    if distance < best_distance:
                        best_distance = distance
                        best_group = group_id
            
            if best_group and best_distance < eps * 1.5:  # More lenient threshold
                face_groups[best_group].append(noise_clip)
                print(f"  Reassigned {Path(noise_clip).name} to {best_group} (distance: {best_distance:.3f})")
            else:
                # Create new group for remaining noise
                new_group_id = f"face_{len(face_groups) + 1:03d}"
                face_groups[new_group_id] = [noise_clip]
                print(f"  Created new group {new_group_id} for {Path(noise_clip).name}")
    
    # Add clips with no faces
    for clip_path in clip_paths:
        clip_path = str(clip_path)
        if clip_path not in clip_paths_list:
            face_groups['no_face'].append(clip_path)
    
    print(f"\nFound {len([g for g in face_groups.keys() if g.startswith('face_')])} face groups")
    print(f"No faces: {len(face_groups.get('no_face', []))} clips")
    
    return dict(face_groups)


def organize_clips(face_groups, output_dir, copy_files=True, create_symlinks=False):
    """
    Organize clips into folders based on face groups.
    
    Args:
        face_groups: Dictionary mapping face_id to list of clip paths
        output_dir: Output directory for organized clips
        copy_files: If True, copy files; if False, move files
        create_symlinks: If True, create symlinks instead of copying/moving
    """
    output_path = ensure_output_dir(Path(output_dir))
    
    print_section("Organizing Clips")
    print(f"Output directory: {output_path}")
    print(f"Mode: {'copy' if copy_files else 'move' if not create_symlinks else 'symlink'}")
    print()
    
    total_clips = 0
    successful = 0
    failed = 0
    
    for group_id, clip_paths in face_groups.items():
        if not clip_paths:
            continue
        
        # Create group directory
        group_dir = output_path / group_id
        group_dir.mkdir(exist_ok=True)
        
        print(f"Group: {group_id} ({len(clip_paths)} clips)")
        
        for clip_path in clip_paths:
            clip_path = Path(clip_path)
            if not clip_path.exists():
                print(f"  ⚠ Skipping (not found): {clip_path.name}")
                failed += 1
                continue
            
            dest_path = group_dir / clip_path.name
            
            # Handle name conflicts
            if dest_path.exists():
                stem = clip_path.stem
                suffix = clip_path.suffix
                counter = 1
                while dest_path.exists():
                    dest_path = group_dir / f"{stem}_{counter}{suffix}"
                    counter += 1
            
            try:
                if create_symlinks:
                    dest_path.symlink_to(clip_path.resolve())
                elif copy_files:
                    shutil.copy2(clip_path, dest_path)
                else:
                    shutil.move(str(clip_path), dest_path)
                
                print(f"  ✓ {clip_path.name} -> {group_id}/")
                successful += 1
                total_clips += 1
                
            except Exception as e:
                print(f"  ✗ Error processing {clip_path.name}: {e}")
                failed += 1
    
    print()
    print_section("Organization Summary")
    print(f"  Successful: {successful}")
    print(f"  Failed: {failed}")
    print(f"  Total clips: {total_clips}")
    print(f"  Output directory: {output_path}")
    print("=" * 60)


def print_summary(face_groups):
    """Print a summary of the grouping results."""
    print_section("Grouping Summary")
    
    # Sort groups by number of clips (descending)
    sorted_groups = sorted(
        [(k, v) for k, v in face_groups.items() if k.startswith('face_')],
        key=lambda x: len(x[1]),
        reverse=True
    )
    
    for group_id, clips in sorted_groups:
        print(f"\n{group_id}: {len(clips)} clip(s)")
        for clip in clips[:5]:  # Show first 5 clips
            print(f"  - {Path(clip).name}")
        if len(clips) > 5:
            print(f"  ... and {len(clips) - 5} more")
    
    # Show noise and no_face groups
    if 'noise' in face_groups and face_groups['noise']:
        print(f"\nnoise: {len(face_groups['noise'])} clip(s) (outliers)")
    if 'no_face' in face_groups and face_groups['no_face']:
        print(f"\nno_face: {len(face_groups['no_face'])} clip(s)")
    
    print("\n" + "=" * 60)
    print(f"Total groups: {len(sorted_groups)}")
    print(f"Total clips: {sum(len(clips) for _, clips in sorted_groups)}")
    print("=" * 60)


def main():
    parser = argparse.ArgumentParser(
        description="Group video clips by detected faces and optionally organize into folders",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --input-dir ./clips/
  %(prog)s --input-dir ./clips/ --organize --output ./organized/
  %(prog)s --input-dir ./clips/ --organize --output ./organized/ --move
  %(prog)s --clips clip1.mov clip2.mov clip3.mov --organize --output ./organized/
        """
    )
    
    parser.add_argument(
        "--input-dir",
        type=str,
        help="Directory containing video clips"
    )
    
    parser.add_argument(
        "--clips",
        nargs="+",
        help="List of video clip paths (alternative to --input-dir)"
    )
    
    parser.add_argument(
        "--output",
        type=str,
        default="face_groups.json",
        help="Output JSON file path (default: face_groups.json)"
    )
    
    parser.add_argument(
        "--organize",
        action="store_true",
        help="Organize clips into folders after grouping"
    )
    
    parser.add_argument(
        "--organize-output",
        type=str,
        help="Output directory for organized clips (required if --organize is used)"
    )
    
    parser.add_argument(
        "--move",
        action="store_true",
        help="Move files instead of copying when organizing (default: copy)"
    )
    
    parser.add_argument(
        "--symlink",
        action="store_true",
        help="Create symlinks instead of copying/moving when organizing"
    )
    
    parser.add_argument(
        "--eps",
        type=float,
        default=0.35,
        help="DBSCAN eps parameter - max distance for same cluster (default: 0.35, lower=stricter)"
    )
    
    parser.add_argument(
        "--min-samples",
        type=int,
        default=2,
        help="DBSCAN min_samples - minimum clips per group (default: 2)"
    )
    
    parser.add_argument(
        "--num-frames",
        type=int,
        default=10,
        help="Number of frames to sample from each video (default: 10)"
    )
    
    parser.add_argument(
        "--extensions",
        nargs="+",
        default=["mov", "mp4", "avi", "mkv"],
        help="Video file extensions to process (default: mov mp4 avi mkv)"
    )
    
    args = parser.parse_args()
    
    # Validate organize arguments
    if args.organize and not args.organize_output:
        parser.error("--organize-output is required when using --organize")
    
    if args.move and args.symlink:
        parser.error("Cannot use both --move and --symlink")
    
    # Collect clip paths
    clip_paths = []
    
    if args.clips:
        clip_paths = [Path(c) for c in args.clips]
    elif args.input_dir:
        input_dir = Path(args.input_dir)
        if not input_dir.exists():
            print(f"ERROR: Input directory not found: {input_dir}", file=sys.stderr)
            sys.exit(1)
        
        extensions = [ext.lower() if not ext.startswith('.') else ext[1:].lower() 
                     for ext in args.extensions]
        
        for ext in extensions:
            clip_paths.extend(input_dir.glob(f"*.{ext}"))
            clip_paths.extend(input_dir.glob(f"*.{ext.upper()}"))
        
        clip_paths = sorted(set(clip_paths))  # Remove duplicates and sort
    else:
        parser.error("Either --input-dir or --clips must be provided")
    
    if not clip_paths:
        print("ERROR: No video clips found", file=sys.stderr)
        sys.exit(1)
    
    print(f"Found {len(clip_paths)} video clip(s)")
    print()
    
    # Group clips by face using clustering
    face_groups = group_clips_by_face_clustering(
        clip_paths,
        eps=args.eps,
        min_samples=args.min_samples,
        num_frames=args.num_frames
    )
    
    # Print summary
    print_summary(face_groups)
    
    # Save results
    output_path = Path(args.output)
    output_path.write_text(json.dumps(face_groups, indent=2), encoding="utf-8")
    print(f"\n✓ Results saved to: {output_path}")
    
    # Organize if requested
    if args.organize:
        copy_files = not args.move and not args.symlink
        create_symlinks = args.symlink
        organize_clips(face_groups, args.organize_output, copy_files, create_symlinks)
    
    print("\n✓ Done!")


if __name__ == "__main__":
    main()
