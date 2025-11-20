#!/usr/bin/env bash
set -euo pipefail

# Source utilities
# Handle symlinks by resolving to actual file first
SCRIPT_FILE="${BASH_SOURCE[0]}"
if [[ -L "$SCRIPT_FILE" ]]; then
    SCRIPT_FILE="$(readlink -f "$SCRIPT_FILE")"
fi
SCRIPT_DIR="$(cd "$(dirname "$SCRIPT_FILE")/.." && pwd)"
source "${SCRIPT_DIR}/utils/common.sh"

# Flags
NO_UPLOAD=false
AUDIO_ONLY=false
VIDEO_ONLY=false

# Parse flags
while [[ $# -gt 0 ]]; do
  case $1 in
    --no-upload|-n)
      NO_UPLOAD=true
      shift
      ;;
    --audio-only|-a)
      AUDIO_ONLY=true
      shift
      ;;
    --video-only|-v)
      VIDEO_ONLY=true
      shift
      ;;
    --help|-h)
      echo "Usage: $0 [FLAGS] INPUT_AUDIO [INPUT_VIDEO] [CUTS_TXT] [OUTPUT_DIR] [s3://bucket/path/]"
      echo "       $0 [FLAGS] INPUT_VIDEO [INPUT_AUDIO] [CUTS_TXT] [OUTPUT_DIR] [s3://bucket/path/]"
      echo
      echo "Create video/audio chunks from input files based on cuts file."
      echo
      echo "Flags:"
      echo "  --no-upload, -n     Disable AWS S3 upload"
      echo "  --audio-only, -a   Force audio-only mode (overrides auto-detection)"
      echo "  --video-only, -v   Force video-only mode (overrides auto-detection)"
      echo
      echo "Arguments:"
      echo "  INPUT_VIDEO = source video file (e.g. big_uhd_prores.mov) - OPTIONAL"
      echo "                If provided alone, uses audio from video file"
      echo "                If provided with audio, processes both video and audio chunks"
      echo "  INPUT_AUDIO = source audio file (e.g. audio.wav) - OPTIONAL"
      echo "                If provided with video, replaces video's audio in output"
      echo "                If provided alone, processes only audio chunks"
      echo "                If omitted with video, uses audio from video file"
      echo "  CUTS_TXT    = optional; text file with: name start_time end_time per line"
      echo "                (default: cuts.txt in script directory)"
      echo "  OUTPUT_DIR  = optional; directory to save chunks (default: current directory)"
      echo "  S3 path     = optional; S3 destination for uploads (required unless --no-upload)"
      echo
      echo "Examples:"
      echo "  $0 video.mov s3://bucket/path/              # Video-only, upload to S3"
      echo "  $0 audio.wav s3://bucket/path/              # Audio-only, upload to S3"
      echo "  $0 video.mov audio.wav s3://bucket/path/    # Both video and audio, upload to S3"
      echo "  $0 --no-upload video.mov                    # Video-only, no upload"
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

# Default to cuts.txt in data directory if not specified
DATA_DIR="${SCRIPT_DIR}/data"
CUTS_FILE_DEFAULT="${DATA_DIR}/cuts.txt"

# Determine if first arg is a video file (check extension or use ffprobe)
if [[ "$#" -lt 1 ]]; then
  echo "Usage: $0 [FLAGS] INPUT_AUDIO [INPUT_VIDEO] [CUTS_TXT] [OUTPUT_DIR] [s3://bucket/path/]"
  echo "       $0 [FLAGS] INPUT_VIDEO [INPUT_AUDIO] [CUTS_TXT] [OUTPUT_DIR] [s3://bucket/path/]"
  echo "Use --help for more information"
  exit 1
fi

# Check if first file is a video file (by extension or content)
FIRST_FILE="$1"
IS_VIDEO=false
if [[ -f "$FIRST_FILE" ]]; then
  # Check by extension
  if [[ "$FIRST_FILE" =~ \.(mov|mp4|mxf|avi|mkv|m4v)$ ]]; then
    IS_VIDEO=true
  # Or check with ffprobe if available
  elif command -v ffprobe >/dev/null 2>&1; then
    if ffprobe -hide_banner -v error -select_streams v:0 -show_entries stream=codec_type -of default=noprint_wrappers=1:nokey=1 "$FIRST_FILE" 2>/dev/null | grep -q "video"; then
      IS_VIDEO=true
    fi
  fi
fi

if [[ "$IS_VIDEO" == "true" ]]; then
  # Video file first: INPUT_VIDEO [INPUT_AUDIO] [CUTS_TXT] ...
  INPUT_VIDEO="$1"
  # Check if second arg is an audio file (not video, not s3, and exists)
  if [[ "$#" -ge 2 ]] && [[ ! "$2" =~ ^s3:// ]]; then
    SECOND_FILE="$2"
    IS_SECOND_AUDIO=false
    if [[ -f "$SECOND_FILE" ]]; then
      # Check if it's not a video file
      if [[ ! "$SECOND_FILE" =~ \.(mov|mp4|mxf|avi|mkv|m4v)$ ]]; then
        # Check if it's an audio file or text file
        if [[ "$SECOND_FILE" =~ \.(wav|aiff|aif|mp3|flac|m4a)$ ]] || \
           command -v ffprobe >/dev/null 2>&1 && ffprobe -hide_banner -v error -select_streams a:0 -show_entries stream=codec_type -of default=noprint_wrappers=1:nokey=1 "$SECOND_FILE" 2>/dev/null | grep -q "audio"; then
          IS_SECOND_AUDIO=true
        fi
      fi
    fi
    
    if [[ "$IS_SECOND_AUDIO" == "true" ]]; then
      # Video then audio: INPUT_VIDEO INPUT_AUDIO [CUTS_TXT] ...
      INPUT_AUDIO="$2"
      # Cuts file is optional, default to cuts.txt
      if [[ "$#" -ge 3 ]] && [[ ! "$3" =~ ^s3:// ]] && [[ -f "$3" ]]; then
        CUTS_FILE="$3"
        shift 3
      elif [[ -f "$CUTS_FILE_DEFAULT" ]]; then
        CUTS_FILE="$CUTS_FILE_DEFAULT"
        shift 2
      else
        log_error "No cuts file specified and default cuts.txt not found in script directory"
        exit 1
      fi
    else
      # Video only: INPUT_VIDEO [CUTS_TXT] ... (use audio from video)
      INPUT_AUDIO=""
      # Second arg might be cuts file
      if [[ -f "$SECOND_FILE" ]]; then
        CUTS_FILE="$2"
        shift 2
      elif [[ -f "$CUTS_FILE_DEFAULT" ]]; then
        CUTS_FILE="$CUTS_FILE_DEFAULT"
        shift 1
      else
        log_error "No cuts file specified and default cuts.txt not found in script directory"
        exit 1
      fi
    fi
    # Override flags only if not explicitly set
    if [[ "$AUDIO_ONLY" != "true" ]] && [[ "$VIDEO_ONLY" != "true" ]]; then
      AUDIO_ONLY=false
      VIDEO_ONLY=false
    fi
  else
    # Video only, no second arg: INPUT_VIDEO [CUTS_TXT] ... (use audio from video)
    INPUT_AUDIO=""
    if [[ -f "$CUTS_FILE_DEFAULT" ]]; then
      CUTS_FILE="$CUTS_FILE_DEFAULT"
      shift 1
    else
      log_error "No cuts file specified and default cuts.txt not found in script directory"
      exit 1
    fi
    # Override flags only if not explicitly set
    if [[ "$AUDIO_ONLY" != "true" ]] && [[ "$VIDEO_ONLY" != "true" ]]; then
      AUDIO_ONLY=false
      VIDEO_ONLY=false
    fi
  fi
else
  # Audio file first: INPUT_AUDIO [INPUT_VIDEO] [CUTS_TXT] ...
  INPUT_AUDIO="$1"
  # Check if second arg is a video file
  if [[ "$#" -ge 2 ]] && [[ ! "$2" =~ ^s3:// ]]; then
    SECOND_FILE="$2"
    IS_SECOND_VIDEO=false
    if [[ -f "$SECOND_FILE" ]]; then
      if [[ "$SECOND_FILE" =~ \.(mov|mp4|mxf|avi|mkv|m4v)$ ]]; then
        IS_SECOND_VIDEO=true
      elif command -v ffprobe >/dev/null 2>&1; then
        if ffprobe -hide_banner -v error -select_streams v:0 -show_entries stream=codec_type -of default=noprint_wrappers=1:nokey=1 "$SECOND_FILE" 2>/dev/null | grep -q "video"; then
          IS_SECOND_VIDEO=true
        fi
      fi
    fi
    
    if [[ "$IS_SECOND_VIDEO" == "true" ]]; then
      # Audio then video: INPUT_AUDIO INPUT_VIDEO [CUTS_TXT] ...
      INPUT_VIDEO="$2"
      # Cuts file is optional
      if [[ "$#" -ge 3 ]] && [[ ! "$3" =~ ^s3:// ]] && [[ -f "$3" ]]; then
        CUTS_FILE="$3"
        shift 3
      elif [[ -f "$CUTS_FILE_DEFAULT" ]]; then
        CUTS_FILE="$CUTS_FILE_DEFAULT"
        shift 2
      else
        log_error "No cuts file specified and default cuts.txt not found in script directory"
        exit 1
      fi
      # Override flags only if not explicitly set
      if [[ "$AUDIO_ONLY" != "true" ]] && [[ "$VIDEO_ONLY" != "true" ]]; then
        AUDIO_ONLY=false
        VIDEO_ONLY=false
      fi
    else
      # Audio only: INPUT_AUDIO [CUTS_TXT] ...
      INPUT_VIDEO=""
      # Second arg might be cuts file or output dir
      if [[ -f "$SECOND_FILE" ]]; then
        CUTS_FILE="$2"
        shift 2
      elif [[ -f "$CUTS_FILE_DEFAULT" ]]; then
        CUTS_FILE="$CUTS_FILE_DEFAULT"
        shift 1
      else
        log_error "No cuts file specified and default cuts.txt not found in script directory"
        exit 1
      fi
      # Auto-detect: audio-only mode (unless flags override)
      if [[ "$VIDEO_ONLY" != "true" ]]; then
        AUDIO_ONLY=true
      fi
      VIDEO_ONLY=false
    fi
  else
    # Only audio file provided
    INPUT_VIDEO=""
    if [[ -f "$CUTS_FILE_DEFAULT" ]]; then
      CUTS_FILE="$CUTS_FILE_DEFAULT"
      shift 1
    else
      log_error "No cuts file specified and default cuts.txt not found in script directory"
      exit 1
    fi
    # Auto-detect: audio-only mode (unless flags override)
    if [[ "$VIDEO_ONLY" != "true" ]]; then
      AUDIO_ONLY=true
    fi
    VIDEO_ONLY=false
  fi
fi

# Determine output directory and S3 destination from remaining args
# If first remaining arg doesn't start with "s3://", it's the output directory
if [[ "$#" -ge 1 ]] && [[ ! "$1" =~ ^s3:// ]]; then
  OUTPUT_DIR="$1"
  if [[ "$#" -ge 2 ]]; then
    S3_DEST="$2"
  else
    if [[ "$NO_UPLOAD" != "true" ]]; then
      log_error "S3 path required unless --no-upload is specified"
      exit 1
    fi
    S3_DEST=""
  fi
else
  OUTPUT_DIR="."  # Current directory
  if [[ "$#" -ge 1 ]]; then
    S3_DEST="$1"
  else
    if [[ "$NO_UPLOAD" != "true" ]]; then
      log_error "S3 path required unless --no-upload is specified"
      exit 1
    fi
    S3_DEST=""
  fi
fi

# Disable upload if flag is set
if [[ "$NO_UPLOAD" == "true" ]]; then
  S3_DEST=""
fi

# Create output directory if it doesn't exist
if [[ ! -d "$OUTPUT_DIR" ]]; then
  echo "Creating output directory: $OUTPUT_DIR"
  mkdir -p "$OUTPUT_DIR"
fi

# Convert to absolute path for clarity
OUTPUT_DIR="$(abs_path "$OUTPUT_DIR")"

print_section "Chunk Configuration"
if [[ "$AUDIO_ONLY" != "true" ]] && [[ -n "$INPUT_VIDEO" ]]; then
  echo "  Input video:     $INPUT_VIDEO"
fi
if [[ -n "$INPUT_AUDIO" ]]; then
  echo "  Input audio:     $INPUT_AUDIO"
else
  echo "  Input audio:     (using audio from video)"
fi
echo "  Cuts file:       $CUTS_FILE"
echo "  Output dir:      $OUTPUT_DIR"
echo "  Mode:            $([ "$AUDIO_ONLY" == "true" ] && echo "AUDIO ONLY" || [ "$VIDEO_ONLY" == "true" ] && echo "VIDEO ONLY" || echo "BOTH")"
if [[ -n "$S3_DEST" ]]; then
  echo "  S3 dest:         $S3_DEST"
else
  echo "  S3 dest:         (none – upload disabled)"
fi
echo "========================================="
echo

# Basic checks
if ! check_ffmpeg || ! check_ffprobe; then
  exit 1
fi

if [[ "$AUDIO_ONLY" != "true" ]] && [[ -n "$INPUT_VIDEO" ]] && ! validate_file "$INPUT_VIDEO"; then
  exit 1
fi

if [[ -n "$INPUT_AUDIO" ]] && ! validate_file "$INPUT_AUDIO"; then
  exit 1
fi

if ! validate_file "$CUTS_FILE"; then
  exit 1
fi

if [[ -n "$S3_DEST" ]] && ! check_aws_cli; then
  log_warning "AWS CLI not found; uploads will be skipped."
  S3_DEST=""
fi

if [[ "$AUDIO_ONLY" != "true" ]] && [[ -n "$INPUT_VIDEO" ]]; then
  echo "===== ffprobe stream info (video 0) ====="
  ffprobe -hide_banner -show_streams -select_streams v:0 -i "$INPUT_VIDEO" 2>&1 | sed 's/^/    /'
  echo "========================================="
  echo
fi

# Detect audio format from audio input file (or video if no separate audio) to match it in output
echo "===== Detecting audio format ====="
AUDIO_SOURCE="${INPUT_AUDIO:-$INPUT_VIDEO}"
AUDIO_SAMPLE_FMT=$(ffprobe -hide_banner -v error -select_streams a:0 -show_entries stream=sample_fmt -of default=noprint_wrappers=1:nokey=1 "$AUDIO_SOURCE" 2>/dev/null | head -1)
AUDIO_SAMPLE_RATE=$(ffprobe -hide_banner -v error -select_streams a:0 -show_entries stream=sample_rate -of default=noprint_wrappers=1:nokey=1 "$AUDIO_SOURCE" 2>/dev/null | head -1)

if [[ -z "$AUDIO_SAMPLE_FMT" ]]; then
  echo "WARNING: Could not detect audio format, defaulting to pcm_f32le"
  AUDIO_CODEC="pcm_f32le"
else
  echo "    Detected sample format: $AUDIO_SAMPLE_FMT"
  echo "    Detected sample rate: ${AUDIO_SAMPLE_RATE:-48000} Hz"
  
  # Map input sample format to appropriate PCM codec
  case "$AUDIO_SAMPLE_FMT" in
    fltp|flt)
      AUDIO_CODEC="pcm_f32le"
      echo "    Using: pcm_f32le (32-bit float)"
      ;;
    s32|s32p)
      AUDIO_CODEC="pcm_s32le"
      echo "    Using: pcm_s32le (32-bit signed integer)"
      ;;
    s24|s24p)
      AUDIO_CODEC="pcm_s24le"
      echo "    Using: pcm_s24le (24-bit signed integer)"
      ;;
    s16|s16p)
      AUDIO_CODEC="pcm_s16le"
      echo "    Using: pcm_s16le (16-bit signed integer)"
      ;;
    u8|u8p)
      AUDIO_CODEC="pcm_u8"
      echo "    Using: pcm_u8 (8-bit unsigned integer)"
      ;;
    *)
      AUDIO_CODEC="pcm_f32le"
      echo "    Unknown format '$AUDIO_SAMPLE_FMT', defaulting to pcm_f32le"
      ;;
  esac
fi
echo "========================================="
echo

# Process each line in cuts file
# Expected format per non-comment line:
#   NAME START_TIME END_TIME
SUCCESSFUL=0
FAILED=0

while read -r NAME START END || [[ -n "$NAME" ]]; do
  # Skip empty lines and comments
  [[ -z "${NAME:-}" ]] && continue
  [[ "$NAME" =~ ^# ]] && continue

  OUT_MOV="${OUTPUT_DIR}/${NAME}.mov"
  OUT_WAV="${OUTPUT_DIR}/${NAME}.wav"

  # Determine which outputs to create
  CREATE_VIDEO=true
  CREATE_AUDIO=true
  if [[ "$AUDIO_ONLY" == "true" ]]; then
    CREATE_VIDEO=false
  fi
  if [[ "$VIDEO_ONLY" == "true" ]]; then
    CREATE_AUDIO=false
  fi

  echo "========================================="
  echo ">>> Clip name: $NAME"
  echo "    Start:     $START"
  echo "    End:       $END"
  if [[ "$CREATE_VIDEO" == "true" ]] && [[ "$CREATE_AUDIO" == "true" ]]; then
    echo "    Outputs:   $OUT_MOV , $OUT_WAV"
  elif [[ "$CREATE_VIDEO" == "true" ]]; then
    echo "    Output:    $OUT_MOV"
  elif [[ "$CREATE_AUDIO" == "true" ]]; then
    echo "    Output:    $OUT_WAV"
  fi
  echo

  # 1) Video clip: video from video file + audio channel 8 from video file
  if [[ "$CREATE_VIDEO" == "true" ]]; then
    if [[ -n "$INPUT_AUDIO" ]]; then
      # Separate audio file provided
      ffmpeg -hide_banner -loglevel info \
        -i "$INPUT_VIDEO" \
        -ss "$START" -to "$END" \
        -i "$INPUT_AUDIO" \
        -ss "$START" -to "$END" \
        -map 0:v \
        -map 0:t? \
        -map_channel 0.0.7 \
        -c:v copy \
        -c:a "$AUDIO_CODEC" \
        ${AUDIO_SAMPLE_RATE:+-ar "$AUDIO_SAMPLE_RATE"} \
        -c:s copy \
        -c:d copy \
        -movflags +write_colr+write_gama+use_metadata_tags+faststart \
        -avoid_negative_ts make_zero \
        -copy_unknown \
        "$OUT_MOV"
    else
      # Use audio from video file
      ffmpeg -hide_banner -loglevel info \
        -i "$INPUT_VIDEO" \
        -ss "$START" -to "$END" \
        -map 0:v \
        -map 0:t? \
        -map_channel 0.0.7 \
        -c:v copy \
        -c:a "$AUDIO_CODEC" \
        ${AUDIO_SAMPLE_RATE:+-ar "$AUDIO_SAMPLE_RATE"} \
        -c:s copy \
        -c:d copy \
        -movflags +write_colr+write_gama+use_metadata_tags+faststart \
        -avoid_negative_ts make_zero \
        -copy_unknown \
        "$OUT_MOV"
    fi

    echo "    Created video clip: $OUT_MOV"
    echo
  fi

  # 2) Audio-only WAV clip (extracted from audio input file or video)
  if [[ "$CREATE_AUDIO" == "true" ]]; then
    AUDIO_SOURCE="${INPUT_AUDIO:-$INPUT_VIDEO}"
    ffmpeg -hide_banner -loglevel info \
      -ss "$START" -to "$END" \
      -i "$AUDIO_SOURCE" \
      -map 0:a:0 \
      -c:a "$AUDIO_CODEC" \
      ${AUDIO_SAMPLE_RATE:+-ar "$AUDIO_SAMPLE_RATE"} \
      "$OUT_WAV"

    echo "    Created audio clip: $OUT_WAV"
    echo
  fi

  # Verify files exist and are not empty before uploading
  if [[ "$CREATE_VIDEO" == "true" ]]; then
    if [[ ! -f "$OUT_MOV" ]] || [[ ! -s "$OUT_MOV" ]]; then
      log_error "Video file $OUT_MOV is missing or empty!"
      ((FAILED++))
      continue
    fi
  fi
  if [[ "$CREATE_AUDIO" == "true" ]]; then
    if [[ ! -f "$OUT_WAV" ]] || [[ ! -s "$OUT_WAV" ]]; then
      log_error "Audio file $OUT_WAV is missing or empty!"
      ((FAILED++))
      continue
    fi
  fi

  # 3) Upload to S3 (multipart handled automatically by AWS CLI for large files)
  if [[ -n "$S3_DEST" ]]; then
    echo "    Uploading to S3 in background..."
    # AWS CLI automatically uses multipart upload for files > 5MB
    if [[ "$CREATE_VIDEO" == "true" ]]; then
      aws s3 cp "$OUT_MOV" "$S3_DEST" \
        --metadata "clip-name=$NAME" &
    fi
    if [[ "$CREATE_AUDIO" == "true" ]]; then
      aws s3 cp "$OUT_WAV" "$S3_DEST" \
        --metadata "clip-name=$NAME" &
    fi
  fi

  ((SUCCESSFUL++))
  echo ">>> Done with clip: $NAME"
  echo "========================================="
  echo

done < "$CUTS_FILE"

# Wait for any background uploads to finish
if [[ -n "$S3_DEST" ]]; then
  echo "Waiting for all AWS uploads to complete..."
  wait
  echo "All uploads completed."
fi

print_summary "$((SUCCESSFUL + FAILED))" "$SUCCESSFUL" "$FAILED" 0

if [[ $FAILED -gt 0 ]]; then
  exit 1
fi

log_success "All clips finished."

