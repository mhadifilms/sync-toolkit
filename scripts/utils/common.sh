#!/usr/bin/env bash
# Common utility functions for scripts
# Source this file: source "$(dirname "$0")/../utils/common.sh"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $*"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $*"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $*"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $*" >&2
}

# Check if a command exists
check_command() {
    local cmd="$1"
    if ! command -v "$cmd" >/dev/null 2>&1; then
        log_error "$cmd not found in PATH"
        return 1
    fi
    return 0
}

# Check for required tools
check_aws_cli() {
    if ! check_command aws; then
        log_error "AWS CLI not found. Please install AWS CLI to use this script."
        return 1
    fi
    return 0
}

check_ffmpeg() {
    if ! check_command ffmpeg; then
        log_error "ffmpeg not found in PATH."
        return 1
    fi
    return 0
}

check_ffprobe() {
    if ! check_command ffprobe; then
        log_error "ffprobe not found in PATH."
        return 1
    fi
    return 0
}

# Validate directory exists
validate_directory() {
    local dir="$1"
    if [[ ! -d "$dir" ]]; then
        log_error "Directory not found: $dir"
        return 1
    fi
    return 0
}

# Validate file exists
validate_file() {
    local file="$1"
    if [[ ! -f "$file" ]]; then
        log_error "File not found: $file"
        return 1
    fi
    return 0
}

# Convert to absolute path
abs_path() {
    local path="$1"
    if [[ -d "$path" ]]; then
        cd "$path" && pwd
    elif [[ -f "$path" ]]; then
        echo "$(cd "$(dirname "$path")" && pwd)/$(basename "$path")"
    else
        echo "$path"
    fi
}

# Count files matching pattern
count_files() {
    local dir="$1"
    local pattern="${2:-*}"
    find "$dir" -maxdepth 1 -type f -name "$pattern" 2>/dev/null | wc -l | tr -d ' '
}

# Check if S3 path exists
s3_exists() {
    local s3_path="$1"
    aws s3 ls "$s3_path" >/dev/null 2>&1
}

# Print section header
print_section() {
    local title="$1"
    echo ""
    echo "========================================="
    echo "$title"
    echo "========================================="
}

# Print summary statistics
print_summary() {
    local total="$1"
    local successful="${2:-0}"
    local failed="${3:-0}"
    local skipped="${4:-0}"
    
    echo ""
    print_section "Summary"
    echo "  Total:      $total"
    echo "  Successful: $successful"
    if [[ $failed -gt 0 ]]; then
        echo "  Failed:     $failed"
    fi
    if [[ $skipped -gt 0 ]]; then
        echo "  Skipped:    $skipped"
    fi
    echo "========================================="
}

