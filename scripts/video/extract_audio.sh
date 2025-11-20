#!/usr/bin/env bash
set -euo pipefail

# Flags
DRY_RUN=false
VERBOSE=false
FORCE=false

# Parse flags
while [[ $# -gt 0 ]]; do
  case $1 in
    --dry-run|-n)
      DRY_RUN=true
      shift
      ;;
    --verbose|-v)
      VERBOSE=true
      shift
      ;;
    --force|-f)
      FORCE=true
      shift
      ;;
    --help|-h)
      echo "Usage: $0 [FLAGS] DIRECTORY"
      echo
      echo "Extracts audio from all video files (mov/mp4) in the specified directory"
      echo "and creates corresponding WAV files with the same name, preserving"
      echo "the original audio bit depth (16/24/32/32float)."
      echo
      echo "Flags:"
      echo "  --dry-run, -n     Show what would be extracted without actually extracting"
      echo "  --verbose, -v     Show detailed information"
      echo "  --force, -f       Overwrite existing WAV files"
      echo
      echo "Arguments:"
      echo "  DIRECTORY  = directory containing video files (required)"
      echo
      echo "Examples:"
      echo "  $0 ./output/              # Extract audio from videos in ./output/"
      echo "  $0 --dry-run ./output/     # Preview what would be extracted"
      echo "  $0 --force ./output/      # Overwrite existing WAV files"
      exit 0
      ;;
    -*)
      echo "Unknown flag: $1"
      echo "Use --help for usage information"
      exit 1
      ;;
    *)
      # Not a flag, break and process as positional arguments
      break
      ;;
  esac
done

if [[ "$#" -lt 1 ]]; then
  echo "Usage: $0 [FLAGS] DIRECTORY"
  echo "Use --help for more information"
  exit 1
fi

TARGET_DIR="$1"

# Validate directory
if [[ ! -d "$TARGET_DIR" ]]; then
  echo "ERROR: Directory not found: $TARGET_DIR"
  exit 1
fi

# Check for required tools
if ! command -v ffmpeg >/dev/null 2>&1; then
  echo "ERROR: ffmpeg not found in PATH."
  exit 1
fi

if ! command -v ffprobe >/dev/null 2>&1; then
  echo "ERROR: ffprobe not found in PATH."
  exit 1
fi

# Convert to absolute path
TARGET_DIR="$(cd "$TARGET_DIR" && pwd)"

echo "Target directory: $TARGET_DIR"
if [[ "$DRY_RUN" == "true" ]]; then
  echo "Mode:            DRY RUN (no files will be created)"
fi
if [[ "$FORCE" == "true" ]]; then
  echo "Mode:            FORCE (will overwrite existing WAV files)"
fi
echo

# Find all video files
VIDEO_FILES=()
while IFS= read -r -d '' file; do
  VIDEO_FILES+=("$file")
done < <(find "$TARGET_DIR" -maxdepth 1 -type f \( \
  -iname "*.mp4" -o \
  -iname "*.mov" \
\) -print0 | sort -z)

if [[ ${#VIDEO_FILES[@]} -eq 0 ]]; then
  echo "No video files (mp4/mov) found in $TARGET_DIR"
  exit 0
fi

echo "Found ${#VIDEO_FILES[@]} video file(s):"
for file in "${VIDEO_FILES[@]}"; do
  filename=$(basename "$file")
  echo "  - $filename"
done
echo

# Function to detect audio format and determine WAV codec
detect_audio_format() {
  local video_file="$1"
  
  # Get audio sample format
  local sample_fmt=$(ffprobe -hide_banner -v error -select_streams a:0 \
    -show_entries stream=sample_fmt -of default=noprint_wrappers=1:nokey=1 \
    "$video_file" 2>/dev/null | head -1)
  
  # Get sample rate
  local sample_rate=$(ffprobe -hide_banner -v error -select_streams a:0 \
    -show_entries stream=sample_rate -of default=noprint_wrappers=1:nokey=1 \
    "$video_file" 2>/dev/null | head -1)
  
  # Get number of channels
  local channels=$(ffprobe -hide_banner -v error -select_streams a:0 \
    -show_entries stream=channels -of default=noprint_wrappers=1:nokey=1 \
    "$video_file" 2>/dev/null | head -1)
  
  # Map input sample format to appropriate PCM codec
  # Common mappings: fltp -> pcm_f32le, s32 -> pcm_s32le, s24 -> pcm_s24le, s16 -> pcm_s16le
  local audio_codec=""
  local bit_depth=""
  
  case "$sample_fmt" in
    fltp|flt)
      audio_codec="pcm_f32le"
      bit_depth="32-bit float"
      ;;
    s32|s32p)
      audio_codec="pcm_s32le"
      bit_depth="32-bit"
      ;;
    s24|s24p)
      audio_codec="pcm_s24le"
      bit_depth="24-bit"
      ;;
    s16|s16p)
      audio_codec="pcm_s16le"
      bit_depth="16-bit"
      ;;
    u8|u8p)
      audio_codec="pcm_u8"
      bit_depth="8-bit"
      ;;
    *)
      # Default to 32-bit float for unknown formats (preserves quality)
      audio_codec="pcm_f32le"
      bit_depth="32-bit float (default)"
      ;;
  esac
  
  echo "$audio_codec|$sample_rate|$channels|$bit_depth|$sample_fmt"
}

# Process each video file
SUCCESSFUL=0
FAILED=0
SKIPPED=0

for video_file in "${VIDEO_FILES[@]}"; do
  video_filename=$(basename "$video_file")
  video_dir=$(dirname "$video_file")
  video_basename="${video_filename%.*}"
  wav_filename="${video_basename}.wav"
  wav_path="${video_dir}/${wav_filename}"
  
  # Check if WAV file already exists
  if [[ -f "$wav_path" ]] && [[ "$FORCE" != "true" ]]; then
    if [[ "$VERBOSE" == "true" ]]; then
      echo "  ⊘ Skipping: $video_filename (WAV already exists: $wav_filename)"
    else
      echo "  ⊘ Skipping: $video_filename"
    fi
    ((SKIPPED++))
    continue
  fi
  
  # Detect audio format
  if [[ "$VERBOSE" == "true" ]]; then
    echo "  Analyzing: $video_filename"
  fi
  
  audio_info=$(detect_audio_format "$video_file")
  IFS='|' read -r audio_codec sample_rate channels bit_depth sample_fmt <<< "$audio_info"
  
  if [[ -z "$audio_codec" ]]; then
    echo "  ✗ ERROR: Could not detect audio format for $video_filename" >&2
    ((FAILED++))
    continue
  fi
  
  if [[ "$VERBOSE" == "true" ]]; then
    echo "    Format: $sample_fmt → $bit_depth"
    echo "    Sample rate: ${sample_rate:-48000} Hz"
    echo "    Channels: ${channels:-2}"
    echo "    Output codec: $audio_codec"
  fi
  
  if [[ "$DRY_RUN" == "true" ]]; then
    echo "  → Would extract: $video_filename → $wav_filename ($bit_depth)"
  else
    # Extract audio preserving format
    loglevel="error"
    [[ "$VERBOSE" == "true" ]] && loglevel="info"
    if ffmpeg -hide_banner -loglevel "$loglevel" -y \
      -i "$video_file" \
      -map 0:a \
      -c:a "$audio_codec" \
      ${sample_rate:+-ar "$sample_rate"} \
      "$wav_path" 2>&1; then
      
      ((SUCCESSFUL++))
      if [[ "$VERBOSE" == "true" ]]; then
        echo "    ✓ Extracted: $wav_filename ($bit_depth)"
      else
        echo "  ✓ $video_filename → $wav_filename"
      fi
    else
      echo "  ✗ ERROR: Failed to extract audio from $video_filename" >&2
      # Remove partial file if it was created
      [[ -f "$wav_path" ]] && rm -f "$wav_path"
      ((FAILED++))
    fi
  fi
  
  if [[ "$VERBOSE" == "true" ]]; then
    echo
  fi
done

echo
echo "========================================="
echo "Extraction Summary:"
echo "  Total videos:    ${#VIDEO_FILES[@]}"
if [[ "$DRY_RUN" != "true" ]]; then
  echo "  Extracted:       $SUCCESSFUL"
  echo "  Failed:          $FAILED"
  echo "  Skipped:         $SKIPPED"
else
  echo "  Would extract:   ${#VIDEO_FILES[@]}"
fi
echo "========================================="

if [[ "$DRY_RUN" != "true" ]] && [[ $FAILED -gt 0 ]]; then
  exit 1
fi

