#!/bin/bash
# WSL-Tmux-Nvim-Setup Checksum Generation Script
#
# Creates SHA256 checksums for release assets to ensure integrity and security.
# Supports multiple hash algorithms and verification modes.

set -euo pipefail  # Strict error mode

# Script metadata
SCRIPT_NAME="$(basename "$0")"
readonly SCRIPT_NAME
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readonly SCRIPT_DIR
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
readonly PROJECT_ROOT

# Default configuration
ASSETS_DIR="${PROJECT_ROOT}/release-assets"
OUTPUT_FILE="checksums.txt"
HASH_ALGORITHM="sha256"
VERIFICATION_MODE="false"
VERBOSE="false"
RECURSIVE="false"

# Supported hash algorithms
readonly SUPPORTED_ALGORITHMS=("md5" "sha1" "sha256" "sha512")

# Color codes for output
readonly RED='\033[0;31m'
readonly GREEN='\033[0;32m'
readonly YELLOW='\033[1;33m'
readonly BLUE='\033[0;34m'
readonly NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${GREEN}[INFO]${NC} $*"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $*"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $*" >&2
}

log_debug() {
    if [[ "$VERBOSE" == "true" ]]; then
        echo -e "${BLUE}[DEBUG]${NC} $*"
    fi
}

# Error handling
error_exit() {
    log_error "FATAL: $1"
    exit "${2:-1}"
}

# Signal handlers
trap 'error_exit "Script interrupted by user" 130' INT TERM

# Validation functions
validate_directory() {
    local dir="$1"
    
    if [[ ! -d "$dir" ]]; then
        error_exit "Directory not found: $dir"
    fi
    
    if [[ ! -r "$dir" ]]; then
        error_exit "Directory not readable: $dir"
    fi
    
    log_debug "Validated directory: $dir"
}

validate_algorithm() {
    local algorithm="$1"
    
    for supported in "${SUPPORTED_ALGORITHMS[@]}"; do
        if [[ "$algorithm" == "$supported" ]]; then
            return 0
        fi
    done
    
    error_exit "Unsupported hash algorithm: $algorithm. Supported: ${SUPPORTED_ALGORITHMS[*]}"
}

check_hash_command() {
    local algorithm="$1"
    local cmd_name
    
    case "$algorithm" in
        "md5")
            cmd_name="md5sum"
            ;;
        "sha1")
            cmd_name="sha1sum"
            ;;
        "sha256")
            cmd_name="sha256sum"
            ;;
        "sha512")
            cmd_name="sha512sum"
            ;;
        *)
            error_exit "Unknown algorithm: $algorithm"
            ;;
    esac
    
    if ! command -v "$cmd_name" >/dev/null 2>&1; then
        error_exit "Command not found: $cmd_name. Please install coreutils package."
    fi
    
    log_debug "Hash command available: $cmd_name"
}

# File discovery functions
find_asset_files() {
    local assets_dir="$1"
    local recursive="$2"
    
    log_debug "Searching for asset files in: $assets_dir"
    
    local find_args=("$assets_dir")
    
    if [[ "$recursive" != "true" ]]; then
        find_args+=("-maxdepth" "1")
    fi
    
    find_args+=("-type" "f")
    
    # Include common release asset patterns
    local patterns=(
        "*.tar.gz"
        "*.zip"
        "*.tar.xz"
        "*.tar.bz2"
        "*.deb"
        "*.rpm"
        "*.dmg"
        "*.exe"
        "*.msi"
        "wsm"
        "install.sh"
    )
    
    local file_list=()
    
    for pattern in "${patterns[@]}"; do
        while IFS= read -r -d '' file; do
            file_list+=("$file")
        done < <(find "${find_args[@]}" -name "$pattern" -print0 2>/dev/null || true)
    done
    
    # Sort and deduplicate
    printf '%s\n' "${file_list[@]}" | sort -u
}

# Checksum generation functions
generate_checksum() {
    local file="$1"
    local algorithm="$2"
    
    if [[ ! -f "$file" ]]; then
        log_warn "File not found: $file"
        return 1
    fi
    
    if [[ ! -r "$file" ]]; then
        log_warn "File not readable: $file"
        return 1
    fi
    
    local hash_cmd
    case "$algorithm" in
        "md5")
            hash_cmd="md5sum"
            ;;
        "sha1")
            hash_cmd="sha1sum"
            ;;
        "sha256")
            hash_cmd="sha256sum"
            ;;
        "sha512")
            hash_cmd="sha512sum"
            ;;
    esac
    
    log_debug "Generating $algorithm checksum for: $(basename "$file")"
    
    # Generate checksum and format output
    local checksum_output
    if checksum_output=$("$hash_cmd" "$file" 2>&1); then
        # Extract just the hash part (before the filename)
        local hash
        hash=$(echo "$checksum_output" | cut -d' ' -f1)
        echo "$hash  $(basename "$file")"
    else
        log_error "Failed to generate checksum for: $file"
        log_error "Command output: $checksum_output"
        return 1
    fi
}

create_checksums_file() {
    local assets_dir="$1"
    local output_file="$2"
    local algorithm="$3"
    local recursive="$4"
    
    log_info "Creating checksums file with $algorithm algorithm"
    
    # Create output directory if needed
    local output_dir
    output_dir="$(dirname "$output_file")"
    mkdir -p "$output_dir"
    
    # Create header for checksums file
    cat > "$output_file" << EOF
# WSL-Tmux-Nvim-Setup Release Checksums
# Generated: $(date -u +"%Y-%m-%d %H:%M:%S UTC")
# Algorithm: $(echo "$algorithm" | tr '[:lower:]' '[:upper:]')
# Source: $assets_dir
#
# Verification Instructions:
# 1. Download both the asset file and this checksums file
# 2. Run: ${algorithm}sum -c checksums.txt
# 3. Ensure output shows "OK" for all files
#
# Format: <hash>  <filename>

EOF
    
    # Find all asset files
    local files
    mapfile -t files < <(find_asset_files "$assets_dir" "$recursive")
    
    if [[ ${#files[@]} -eq 0 ]]; then
        log_warn "No asset files found in: $assets_dir"
        return 1
    fi
    
    log_info "Found ${#files[@]} files to checksum"
    
    # Generate checksums
    local success_count=0
    local total_count=0
    
    for file in "${files[@]}"; do
        ((total_count++))
        
        local checksum_line
        if checksum_line=$(generate_checksum "$file" "$algorithm"); then
            echo "$checksum_line" >> "$output_file"
            ((success_count++))
            
            if [[ "$VERBOSE" == "true" ]]; then
                log_info "✓ $(basename "$file")"
            fi
        else
            log_error "✗ Failed to checksum: $(basename "$file")"
        fi
    done
    
    # Add footer with statistics
    cat >> "$output_file" << EOF

# Checksum Statistics:
# Total files: $total_count
# Successfully checksummed: $success_count
# Failed: $((total_count - success_count))
EOF
    
    log_info "Checksums file created: $output_file"
    log_info "Successfully checksummed: $success_count/$total_count files"
    
    return 0
}

# Verification functions
verify_checksums() {
    local checksums_file="$1"
    local algorithm="$2"
    
    if [[ ! -f "$checksums_file" ]]; then
        error_exit "Checksums file not found: $checksums_file"
    fi
    
    log_info "Verifying checksums from: $checksums_file"
    
    local hash_cmd
    case "$algorithm" in
        "md5")
            hash_cmd="md5sum"
            ;;
        "sha1")
            hash_cmd="sha1sum"
            ;;
        "sha256")
            hash_cmd="sha256sum"
            ;;
        "sha512")
            hash_cmd="sha512sum"
            ;;
    esac
    
    # Change to the directory containing the checksums file
    local checksums_dir
    checksums_dir="$(dirname "$checksums_file")"
    local checksums_filename
    checksums_filename="$(basename "$checksums_file")"
    
    cd "$checksums_dir" || error_exit "Cannot change to directory: $checksums_dir"
    
    # Run verification
    local verification_output
    local verification_exit_code
    
    verification_output=$("$hash_cmd" -c "$checksums_filename" 2>&1)
    verification_exit_code=$?
    
    # Parse results
    local ok_count=0
    local fail_count=0
    local missing_count=0
    
    while IFS= read -r line; do
        if [[ "$line" =~ :[[:space:]]*OK$ ]]; then
            ((ok_count++))
            if [[ "$VERBOSE" == "true" ]]; then
                log_info "✓ $line"
            fi
        elif [[ "$line" =~ :[[:space:]]*FAILED$ ]]; then
            ((fail_count++))
            log_error "✗ $line"
        elif [[ "$line" =~ :[[:space:]]*FAILED[[:space:]]*open[[:space:]]*or[[:space:]]*read ]]; then
            ((missing_count++))
            log_error "✗ $line"
        fi
    done <<< "$verification_output"
    
    # Report results
    echo
    log_info "Verification Summary:"
    log_info "  ✓ Passed: $ok_count"
    
    if [[ $fail_count -gt 0 ]]; then
        log_error "  ✗ Failed: $fail_count"
    fi
    
    if [[ $missing_count -gt 0 ]]; then
        log_error "  ? Missing: $missing_count"
    fi
    
    if [[ $verification_exit_code -eq 0 ]]; then
        log_info "All checksums verified successfully!"
        return 0
    else
        log_error "Checksum verification failed!"
        return 1
    fi
}

# Usage information
usage() {
    cat << EOF
Usage: $SCRIPT_NAME [OPTIONS]

Generate SHA256 checksums for release assets with security verification.

OPTIONS:
    -d, --directory DIR      Assets directory (default: ./release-assets)
    -o, --output FILE        Output checksums file (default: checksums.txt)
    -a, --algorithm ALGO     Hash algorithm: ${SUPPORTED_ALGORITHMS[*]} (default: sha256)
    -r, --recursive          Search subdirectories recursively
    -v, --verify FILE        Verify existing checksums file
    --verbose               Enable verbose output
    -h, --help              Show this help message

EXAMPLES:
    $SCRIPT_NAME                                    # Create SHA256 checksums
    $SCRIPT_NAME -a sha512 -o checksums-sha512.txt # Use SHA512
    $SCRIPT_NAME -d /path/to/assets --recursive     # Include subdirectories
    $SCRIPT_NAME --verify checksums.txt            # Verify existing checksums

SECURITY NOTES:
    - SHA256 is recommended for release verification
    - Always verify checksums after downloading assets
    - Store checksums separately from assets when possible
    - Use HTTPS for downloading both assets and checksums

EOF
}

# Argument parsing
parse_arguments() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            -d|--directory)
                ASSETS_DIR="$2"
                shift 2
                ;;
            -o|--output)
                OUTPUT_FILE="$2"
                shift 2
                ;;
            -a|--algorithm)
                HASH_ALGORITHM="$2"
                shift 2
                ;;
            -r|--recursive)
                RECURSIVE="true"
                shift
                ;;
            -v|--verify)
                VERIFICATION_MODE="true"
                OUTPUT_FILE="$2"
                shift 2
                ;;
            --verbose)
                VERBOSE="true"
                shift
                ;;
            -h|--help)
                usage
                exit 0
                ;;
            *)
                error_exit "Unknown option: $1"
                ;;
        esac
    done
}

# Main execution
main() {
    parse_arguments "$@"
    
    log_debug "Starting checksum operations"
    log_debug "Assets directory: $ASSETS_DIR"
    log_debug "Output file: $OUTPUT_FILE"
    log_debug "Hash algorithm: $HASH_ALGORITHM"
    log_debug "Recursive: $RECURSIVE"
    log_debug "Verification mode: $VERIFICATION_MODE"
    
    # Validation
    validate_algorithm "$HASH_ALGORITHM"
    check_hash_command "$HASH_ALGORITHM"
    
    if [[ "$VERIFICATION_MODE" == "true" ]]; then
        # Verification mode
        verify_checksums "$OUTPUT_FILE" "$HASH_ALGORITHM"
    else
        # Generation mode
        validate_directory "$ASSETS_DIR"
        
        # Convert relative paths to absolute
        ASSETS_DIR="$(readlink -f "$ASSETS_DIR")"
        
        # If output file is relative, make it relative to assets directory
        if [[ "$OUTPUT_FILE" != /* ]]; then
            OUTPUT_FILE="${ASSETS_DIR}/${OUTPUT_FILE}"
        fi
        
        create_checksums_file "$ASSETS_DIR" "$OUTPUT_FILE" "$HASH_ALGORITHM" "$RECURSIVE"
        
        # Display final information
        echo
        log_info "Checksums operation completed!"
        log_info "Output file: $OUTPUT_FILE"
        log_info "Algorithm: $HASH_ALGORITHM"
        
        # Show file size and location
        if [[ -f "$OUTPUT_FILE" ]]; then
            local file_size
            file_size=$(du -h "$OUTPUT_FILE" | cut -f1)
            log_info "File size: $file_size"
            
            if [[ "$VERBOSE" == "true" ]]; then
                echo
                echo "Contents preview:"
                echo "==================="
                head -n 20 "$OUTPUT_FILE"
                echo "..."
            fi
        fi
    fi
}

# Execute main function with all arguments
main "$@"
