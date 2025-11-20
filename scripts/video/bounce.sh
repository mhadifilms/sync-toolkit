#!/usr/bin/env bash
set +e  # Don't exit on errors - warnings from ffmpeg/ffprobe shouldn't stop processing
set -u  # Still catch undefined variables
set -o pipefail  # But allow pipe failures

# Source utilities
# Handle symlinks by resolving to actual file first
SCRIPT_FILE="${BASH_SOURCE[0]}"
if [[ -L "$SCRIPT_FILE" ]]; then
    SCRIPT_FILE="$(readlink -f "$SCRIPT_FILE")"
fi
SCRIPT_DIR="$(cd "$(dirname "$SCRIPT_FILE")/.." && pwd)"
source "${SCRIPT_DIR}/utils/common.sh"

# Flags
DRY_RUN=false
VERBOSE=false
FORCE=false
OUTPUT_DIR=""
RECURSIVE=false

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
    --output|-o)
      OUTPUT_DIR="$2"
      shift 2
      ;;
    --recursive|-r)
      RECURSIVE=true
      shift
      ;;
    --help|-h)
      echo "Usage: $0 [FLAGS] INPUT_DIRECTORY [INPUT_DIRECTORY2 ...]"
      echo
      echo "Creates 'bounced' versions of all MOV files in the specified directory(ies)."
      echo "A bounced video consists of: [original video + original audio] + [reversed video + reversed audio] + [original video + original audio]"
      echo "with zero frame loss or additional black frames."
      echo
      echo "Flags:"
      echo "  --dry-run, -n        Show what would be processed without actually processing"
      echo "  --verbose, -v       Show detailed information"
      echo "  --force, -f          Overwrite existing bounced files"
      echo "  --output, -o DIR     Output directory (default: same as input directory)"
      echo "  --recursive, -r      Process all subdirectories recursively"
      echo
      echo "Arguments:"
      echo "  INPUT_DIRECTORY  = directory containing MOV files (required)"
      echo "                    Can specify multiple directories"
      echo
      echo "Examples:"
      echo "  $0 ./videos/                           # Process all MOVs in ./videos/"
      echo "  $0 --dry-run ./videos/                 # Preview what would be processed"
      echo "  $0 --output ./bounced/ ./videos/       # Save bounced videos to ./bounced/"
      echo "  $0 --force ./videos/                  # Overwrite existing bounced files"
      echo "  $0 --recursive ./base_dir/            # Process all subdirectories"
      echo "  $0 ./dir1/ ./dir2/ ./dir3/             # Process multiple directories"
      exit 0
      ;;
    -*)
      echo "Unknown flag: $1"
      echo "Use --help for usage information"
      exit 1
      ;;
    *)
      break
      ;;
  esac
done

if [[ "$#" -lt 1 ]]; then
  echo "Usage: $0 [FLAGS] INPUT_DIRECTORY [INPUT_DIRECTORY2 ...]"
  echo "Use --help for more information"
  exit 1
fi

# Check for required tools
if ! check_ffmpeg || ! check_ffprobe; then
  exit 1
fi

# Function to detect video properties
detect_video_properties() {
  local video_file="$1"
  
  local codec=$(ffprobe -hide_banner -v error -select_streams v:0 \
    -show_entries stream=codec_name -of default=noprint_wrappers=1:nokey=1 \
    "$video_file" 2>/dev/null | head -1)
  
  local fps=$(ffprobe -hide_banner -v error -select_streams v:0 \
    -show_entries stream=r_frame_rate -of default=noprint_wrappers=1:nokey=1 \
    "$video_file" 2>/dev/null | head -1)
  
  local pix_fmt=$(ffprobe -hide_banner -v error -select_streams v:0 \
    -show_entries stream=pix_fmt -of default=noprint_wrappers=1:nokey=1 \
    "$video_file" 2>/dev/null | head -1)
  
  local width=$(ffprobe -hide_banner -v error -select_streams v:0 \
    -show_entries stream=width -of default=noprint_wrappers=1:nokey=1 \
    "$video_file" 2>/dev/null | head -1)
  
  local height=$(ffprobe -hide_banner -v error -select_streams v:0 \
    -show_entries stream=height -of default=noprint_wrappers=1:nokey=1 \
    "$video_file" 2>/dev/null | head -1)
  
  local audio_codec=$(ffprobe -hide_banner -v error -select_streams a:0 \
    -show_entries stream=codec_name -of default=noprint_wrappers=1:nokey=1 \
    "$video_file" 2>/dev/null | head -1)
  
  local audio_sample_fmt=$(ffprobe -hide_banner -v error -select_streams a:0 \
    -show_entries stream=sample_fmt -of default=noprint_wrappers=1:nokey=1 \
    "$video_file" 2>/dev/null | head -1)
  
  local audio_sample_rate=$(ffprobe -hide_banner -v error -select_streams a:0 \
    -show_entries stream=sample_rate -of default=noprint_wrappers=1:nokey=1 \
    "$video_file" 2>/dev/null | head -1)
  
  local audio_channels=$(ffprobe -hide_banner -v error -select_streams a:0 \
    -show_entries stream=channels -of default=noprint_wrappers=1:nokey=1 \
    "$video_file" 2>/dev/null | head -1)
  
  local bitrate=$(ffprobe -hide_banner -v error -select_streams v:0 \
    -show_entries stream=bit_rate -of default=noprint_wrappers=1:nokey=1 \
    "$video_file" 2>/dev/null | head -1)
  
  local profile=""
  if [[ "$codec" == "prores" ]]; then
    profile=$(ffprobe -hide_banner -v error -select_streams v:0 \
      -show_entries stream=profile -of default=noprint_wrappers=1:nokey=1 \
      "$video_file" 2>/dev/null | head -1)
  fi
  
  echo "$codec|$fps|$pix_fmt|${width}x${height}|$audio_codec|$audio_sample_fmt|$audio_sample_rate|$audio_channels|$bitrate|$profile"
}

# Function to process a single directory
process_directory() {
  local INPUT_DIR="$1"
  local OUTPUT_DIR_LOCAL="${2:-$INPUT_DIR}"
  
  # Convert to absolute paths
  INPUT_DIR="$(abs_path "$INPUT_DIR")"
  if [[ ! -d "$INPUT_DIR" ]]; then
    log_error "Directory not found: $INPUT_DIR"
    return 1
  fi
  
  if [[ -n "$OUTPUT_DIR_LOCAL" ]] && [[ "$OUTPUT_DIR_LOCAL" != "$INPUT_DIR" ]]; then
    OUTPUT_DIR_LOCAL="$(abs_path "$OUTPUT_DIR_LOCAL" 2>/dev/null || echo "$(cd "$(dirname "$OUTPUT_DIR_LOCAL")" && pwd)/$(basename "$OUTPUT_DIR_LOCAL")")"
    mkdir -p "$OUTPUT_DIR_LOCAL"
  else
    OUTPUT_DIR_LOCAL="$INPUT_DIR"
  fi
  
  # Find all MOV files (exclude already-bounced files)
  VIDEO_FILES=()
  if [[ "$RECURSIVE" == "true" ]]; then
    while IFS= read -r -d '' file; do
      if [[ "$(basename "$file")" != *_bounced.mov ]]; then
        VIDEO_FILES+=("$file")
      fi
    done < <(find "$INPUT_DIR" -type f -iname "*.mov" -print0 | sort -z)
  else
    while IFS= read -r -d '' file; do
      if [[ "$(basename "$file")" != *_bounced.mov ]]; then
        VIDEO_FILES+=("$file")
      fi
    done < <(find "$INPUT_DIR" -maxdepth 1 -type f -iname "*.mov" -print0 | sort -z)
  fi
  
  if [[ ${#VIDEO_FILES[@]} -eq 0 ]]; then
    if [[ "$VERBOSE" == "true" ]]; then
      log_info "No MOV files found in $INPUT_DIR"
    fi
    return 0
  fi
  
  if [[ "$VERBOSE" == "true" ]] || [[ ${#VIDEO_FILES[@]} -gt 1 ]]; then
    echo ""
    print_section "Processing: $(basename "$INPUT_DIR")"
    echo "  Found ${#VIDEO_FILES[@]} MOV file(s)"
    if [[ "$VERBOSE" == "true" ]]; then
      for file in "${VIDEO_FILES[@]}"; do
        echo "    - $(basename "$file")"
      done
    fi
    echo "========================================="
    echo
  fi
  
  # Process each video file
  SUCCESSFUL=0
  FAILED=0
  SKIPPED=0
  
  for video_file in "${VIDEO_FILES[@]}"; do
    video_filename=$(basename "$video_file")
    video_dir=$(dirname "$video_file")
    video_basename="${video_filename%.*}"
    bounced_filename="${video_basename}_bounced.mov"
    
    # Preserve directory structure if recursive
    if [[ "$RECURSIVE" == "true" ]] && [[ "$OUTPUT_DIR_LOCAL" != "$INPUT_DIR" ]]; then
      rel_path="${video_file#$INPUT_DIR/}"
      rel_dir=$(dirname "$rel_path")
      bounced_path="${OUTPUT_DIR_LOCAL}/${rel_dir}/${bounced_filename}"
      mkdir -p "$(dirname "$bounced_path")"
    else
      bounced_path="${OUTPUT_DIR_LOCAL}/${bounced_filename}"
    fi
    
    # Check if bounced file already exists
    if [[ -f "$bounced_path" ]] && [[ "$FORCE" != "true" ]]; then
      if [[ "$VERBOSE" == "true" ]]; then
        echo "  ⊘ Skipping: $video_filename (bounced file already exists)"
      else
        echo "  ⊘ Skipping: $video_filename"
      fi
      ((SKIPPED++))
      continue
    fi
    
    # Detect video properties
    if [[ "$VERBOSE" == "true" ]]; then
      echo "  Analyzing: $video_filename"
    fi
    
    video_info=$(detect_video_properties "$video_file")
    IFS='|' read -r codec fps pix_fmt resolution audio_codec audio_sample_fmt audio_sample_rate audio_channels bitrate profile <<< "$video_info"
    
    if [[ -z "$codec" ]]; then
      log_error "Could not detect video codec for $video_filename"
      ((FAILED++))
      continue
    fi
    
    if [[ "$VERBOSE" == "true" ]]; then
      echo "    Video codec: $codec"
      echo "    FPS: $fps"
      echo "    Resolution: $resolution"
      echo "    Pixel format: $pix_fmt"
      echo "    Audio codec: $audio_codec"
      echo "    Audio sample format: $audio_sample_fmt"
      echo "    Audio sample rate: ${audio_sample_rate:-48000} Hz"
      echo "    Audio channels: ${audio_channels:-2}"
    fi
    
    if [[ "$DRY_RUN" == "true" ]]; then
      echo "  → Would create: $video_filename → $bounced_filename"
    else
      # Determine video codec settings
      VIDEO_CODEC_ARGS=""
      if [[ "$codec" == "prores" ]]; then
        profile_num=""
        if [[ -n "$profile" ]]; then
          case "$profile" in
            proxy|Proxy|PROXY|0) profile_num="0" ;;
            lt|LT|1) profile_num="1" ;;
            standard|Standard|STANDARD|2) profile_num="2" ;;
            hq|HQ|3) profile_num="3" ;;
            4444|4) profile_num="4" ;;
            xq|XQ|5) profile_num="5" ;;
            *) profile_num="3" ;;
          esac
          VIDEO_CODEC_ARGS="-c:v prores -profile:v $profile_num"
        else
          VIDEO_CODEC_ARGS="-c:v prores -profile:v 3"
        fi
      else
        VIDEO_CODEC_ARGS="-c:v $codec"
      fi
      
      # Determine audio codec settings
      AUDIO_CODEC_ARGS=""
      if [[ -n "$audio_codec" ]]; then
        case "$audio_sample_fmt" in
          fltp|flt) AUDIO_CODEC_ARGS="-c:a pcm_f32le" ;;
          s32|s32p) AUDIO_CODEC_ARGS="-c:a pcm_s32le" ;;
          s24|s24p) AUDIO_CODEC_ARGS="-c:a pcm_s24le" ;;
          s16|s16p) AUDIO_CODEC_ARGS="-c:a pcm_s16le" ;;
          *)
            if [[ "$audio_codec" == "pcm_s24le" ]] || [[ "$audio_codec" == "pcm_s32le" ]] || \
               [[ "$audio_codec" == "pcm_f32le" ]] || [[ "$audio_codec" == "pcm_s16le" ]]; then
              AUDIO_CODEC_ARGS="-c:a $audio_codec"
            else
              AUDIO_CODEC_ARGS="-c:a pcm_f32le"
            fi
            ;;
        esac
      else
        AUDIO_CODEC_ARGS="-c:a pcm_f32le"
      fi
      
      loglevel="error"
      [[ "$VERBOSE" == "true" ]] && loglevel="info"
      
      if ffmpeg -hide_banner -loglevel "$loglevel" -y \
        -i "$video_file" \
        -filter_complex "[0:v]reverse[vrev];[0:a:0]areverse[arev];[0:v][0:a:0][vrev][arev][0:v][0:a:0]concat=n=3:v=1:a=1[vout][aout]" \
        -map "[vout]" \
        -map "[aout]" \
        $VIDEO_CODEC_ARGS \
        $AUDIO_CODEC_ARGS \
        ${audio_sample_rate:+-ar "$audio_sample_rate"} \
        ${fps:+-r "$fps"} \
        ${pix_fmt:+-pix_fmt "$pix_fmt"} \
        -movflags +write_colr+write_gama+use_metadata_tags+faststart \
        -avoid_negative_ts make_zero \
        "$bounced_path" 2>&1 | grep -v "Referenced QT chapter"; then
        
        ((SUCCESSFUL++))
        if [[ "$VERBOSE" == "true" ]]; then
          echo "    ✓ Created: $bounced_filename"
        else
          echo "  ✓ $video_filename → $bounced_filename"
        fi
      else
        log_error "Failed to create bounced version of $video_filename"
        [[ -f "$bounced_path" ]] && rm -f "$bounced_path"
        ((FAILED++))
      fi
    fi
    
    if [[ "$VERBOSE" == "true" ]]; then
      echo
    fi
  done
  
  # Return summary
  echo "$SUCCESSFUL|$FAILED|$SKIPPED|${#VIDEO_FILES[@]}"
}

# Process all input directories
TOTAL_SUCCESSFUL=0
TOTAL_FAILED=0
TOTAL_SKIPPED=0
TOTAL_VIDEOS=0

for INPUT_DIR in "$@"; do
  if [[ "$RECURSIVE" == "true" ]]; then
    # Process directory and all subdirectories
    if [[ -d "$INPUT_DIR" ]]; then
      for subdir in "$INPUT_DIR"/*/; do
        if [[ -d "$subdir" ]]; then
          result=$(process_directory "$subdir" "$OUTPUT_DIR")
          IFS='|' read -r successful failed skipped total <<< "$result"
          TOTAL_SUCCESSFUL=$((TOTAL_SUCCESSFUL + successful))
          TOTAL_FAILED=$((TOTAL_FAILED + failed))
          TOTAL_SKIPPED=$((TOTAL_SKIPPED + skipped))
          TOTAL_VIDEOS=$((TOTAL_VIDEOS + total))
        fi
      done
    fi
  else
    # Process single directory
    result=$(process_directory "$INPUT_DIR" "$OUTPUT_DIR")
    IFS='|' read -r successful failed skipped total <<< "$result"
    TOTAL_SUCCESSFUL=$((TOTAL_SUCCESSFUL + successful))
    TOTAL_FAILED=$((TOTAL_FAILED + failed))
    TOTAL_SKIPPED=$((TOTAL_SKIPPED + skipped))
    TOTAL_VIDEOS=$((TOTAL_VIDEOS + total))
  fi
done

echo
print_section "Bounce Summary"
echo "  Total videos:    $TOTAL_VIDEOS"
if [[ "$DRY_RUN" != "true" ]]; then
  echo "  Created:         $TOTAL_SUCCESSFUL"
  echo "  Failed:          $TOTAL_FAILED"
  echo "  Skipped:         $TOTAL_SKIPPED"
else
  echo "  Would create:    $TOTAL_VIDEOS"
fi
echo "========================================="

if [[ "$DRY_RUN" != "true" ]] && [[ $TOTAL_FAILED -gt 0 ]]; then
  exit 1
fi

