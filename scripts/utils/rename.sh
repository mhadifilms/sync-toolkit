#!/usr/bin/env bash
set -euo pipefail

# Flags
DRY_RUN=false
VERBOSE=false

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
    --help|-h)
      echo "Usage: $0 [FLAGS] DIRECTORY"
      echo
      echo "Renames video (mp4/mov) and audio (mp3/wav) files in the specified directory"
      echo "to sequential numbers (01, 02, 03...) based on original creation date."
      echo "Each file type is numbered separately (01.mov, 01.wav, 02.mov, 02.wav, etc.)"
      echo
      echo "Flags:"
      echo "  --dry-run, -n     Show what would be renamed without actually renaming"
      echo "  --verbose, -v     Show detailed information"
      echo
      echo "Arguments:"
      echo "  DIRECTORY  = directory containing files to rename (required)"
      echo
      echo "Examples:"
      echo "  $0 ./output/              # Rename files in ./output/"
      echo "  $0 --dry-run ./output/     # Preview what would be renamed"
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

# Convert to absolute path
TARGET_DIR="$(cd "$TARGET_DIR" && pwd)"

echo "Target directory: $TARGET_DIR"
if [[ "$DRY_RUN" == "true" ]]; then
  echo "Mode:            DRY RUN (no files will be renamed)"
fi
echo

# Find all video and audio files and group by extension
# Supported: mp4, mov, mp3, wav
declare -A FILES_BY_EXT

while IFS= read -r -d '' file; do
  extension="${file##*.}"
  extension=$(echo "$extension" | tr '[:upper:]' '[:lower:]')
  FILES_BY_EXT["$extension"]+="$file"$'\0'
done < <(find "$TARGET_DIR" -maxdepth 1 -type f \( \
  -iname "*.mp4" -o \
  -iname "*.mov" -o \
  -iname "*.mp3" -o \
  -iname "*.wav" \
\) -print0)

# Count total files
TOTAL_FILES=0
for ext in "${!FILES_BY_EXT[@]}"; do
  count=$(echo -n "${FILES_BY_EXT[$ext]}" | tr '\0' '\n' | wc -l | tr -d ' ')
  ((TOTAL_FILES += count))
done

if [[ $TOTAL_FILES -eq 0 ]]; then
  echo "No video (mp4/mov) or audio (mp3/wav) files found in $TARGET_DIR"
  exit 0
fi

echo "Found $TOTAL_FILES file(s) to process:"
for ext in "${!FILES_BY_EXT[@]}"; do
  count=$(echo -n "${FILES_BY_EXT[$ext]}" | tr '\0' '\n' | wc -l | tr -d ' ')
  echo "  - $count .$ext file(s)"
done
echo

# Function to get creation date
get_creation_date() {
  local file="$1"
  # Try macOS stat format first
  if CREATION_DATE=$(stat -f %B "$file" 2>/dev/null); then
    echo "$CREATION_DATE"
  # Try Linux stat format
  elif CREATION_DATE=$(stat -c %W "$file" 2>/dev/null); then
    echo "$CREATION_DATE"
  # Fall back to modification time if creation time not available
  elif CREATION_DATE=$(stat -f %m "$file" 2>/dev/null || stat -c %Y "$file" 2>/dev/null); then
    echo "$CREATION_DATE"
  else
    echo "0"
  fi
}

# Function to sort and rename files by extension
rename_by_extension() {
  local ext="$1"
  local files_str="${FILES_BY_EXT[$ext]}"
  
  if [[ -z "$files_str" ]]; then
    return
  fi
  
  # Convert null-separated string to array
  local -a files
  while IFS= read -r -d '' file; do
    files+=("$file")
  done < <(echo -n "$files_str")
  
  if [[ ${#files[@]} -eq 0 ]]; then
    return
  fi
  
  echo "Processing .$ext files (${#files[@]} file(s)):"
  
  # Get creation dates and sort files by creation date
  declare -A FILE_DATES
  for file in "${files[@]}"; do
    FILE_DATES["$file"]=$(get_creation_date "$file")
  done
  
  # Sort files by creation date
  IFS=$'\n' SORTED_FILES=($(
    for file in "${files[@]}"; do
      echo "${FILE_DATES[$file]}|$file"
    done | sort -t'|' -k1 -n | cut -d'|' -f2-
  ))
  
  if [[ "$VERBOSE" == "true" ]]; then
    for i in "${!SORTED_FILES[@]}"; do
      file="${SORTED_FILES[$i]}"
      filename=$(basename "$file")
      date_str=$(date -r "${FILE_DATES[$file]}" "+%Y-%m-%d %H:%M:%S" 2>/dev/null || date -d "@${FILE_DATES[$file]}" "+%Y-%m-%d %H:%M:%S" 2>/dev/null || echo "unknown")
      echo "    $((i+1)). $filename (created: $date_str)"
    done
  fi
  
  if [[ "$DRY_RUN" == "true" ]]; then
    echo "  Would rename:"
  fi
  
  # Rename files sequentially
  local renamed_count=0
  local failed_count=0
  
  for i in "${!SORTED_FILES[@]}"; do
    file="${SORTED_FILES[$i]}"
    filename=$(basename "$file")
    dirname=$(dirname "$file")
    
    # Generate new filename with zero-padded number
    new_number=$(printf "%02d" $((i+1)))
    new_filename="${new_number}.${ext}"
    new_path="${dirname}/${new_filename}"
    
    # Skip if filename is already correct
    if [[ "$filename" == "$new_filename" ]]; then
      if [[ "$VERBOSE" == "true" ]]; then
        echo "    → Skipping (already named correctly): $filename"
      fi
      continue
    fi
    
    # Check if target filename already exists (and it's not the same file)
    if [[ -f "$new_path" ]] && [[ "$new_path" != "$file" ]]; then
      echo "    ✗ ERROR: Target file already exists: $new_filename" >&2
      ((failed_count++))
      continue
    fi
    
    if [[ "$DRY_RUN" == "true" ]]; then
      echo "    $filename → $new_filename"
    else
      if mv "$file" "$new_path" 2>/dev/null; then
        ((renamed_count++))
        if [[ "$VERBOSE" == "true" ]]; then
          echo "    ✓ Renamed: $filename → $new_filename"
        else
          echo "    ✓ $filename → $new_filename"
        fi
      else
        echo "    ✗ ERROR: Failed to rename $filename" >&2
        ((failed_count++))
      fi
    fi
  done
  
  if [[ "$DRY_RUN" != "true" ]]; then
    echo "  Renamed: $renamed_count, Failed: $failed_count"
  fi
  echo
}

# Process each extension type separately
TOTAL_RENAMED=0
TOTAL_FAILED=0

# Process in order: mov, mp4, wav, mp3
for ext in mov mp4 wav mp3; do
  if [[ -n "${FILES_BY_EXT[$ext]:-}" ]]; then
    rename_by_extension "$ext"
  fi
done

echo "========================================="
if [[ "$DRY_RUN" == "true" ]]; then
  echo "Dry Run Summary:"
  echo "  Total files:    $TOTAL_FILES"
  echo "  Would rename:   $TOTAL_FILES"
else
  echo "Rename Summary:"
  echo "  Total files:    $TOTAL_FILES"
fi
echo "========================================="

if [[ "$DRY_RUN" != "true" ]] && [[ $TOTAL_FAILED -gt 0 ]]; then
  exit 1
fi
