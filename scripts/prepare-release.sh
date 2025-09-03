#!/bin/bash
# WSL-Tmux-Nvim-Setup Release Asset Preparation Script
#
# This script prepares release assets by creating structured archives
# with all necessary configuration files, documentation, and installation scripts.
# Follows POSIX compliance and implements robust error handling.

set -euo pipefail  # Strict error mode

# Script metadata
declare SCRIPT_NAME
SCRIPT_NAME="$(basename "$0")"
readonly SCRIPT_NAME

declare SCRIPT_DIR
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readonly SCRIPT_DIR

declare PROJECT_ROOT
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
readonly PROJECT_ROOT

# Default values
VERSION=""
OUTPUT_FORMAT="both"  # tar.gz, zip, or both
INCLUDE_DOCS="true"
VERBOSE="false"
RELEASE_DIR="${PROJECT_ROOT}/release-assets"  # Default output directory

# Color codes for output
readonly RED='\033[0;31m'
readonly GREEN='\033[0;32m'
readonly YELLOW='\033[1;33m'
readonly BLUE='\033[0;34m'
readonly NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${GREEN}[INFO]${NC} $*" >&2
    if [[ -n "${LOG_FILE:-}" ]]; then
        echo "[INFO] $*" >> "$LOG_FILE" 2>/dev/null || true
    fi
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $*" >&2
    if [[ -n "${LOG_FILE:-}" ]]; then
        echo "[WARN] $*" >> "$LOG_FILE" 2>/dev/null || true
    fi
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $*" >&2
    if [[ -n "${LOG_FILE:-}" ]]; then
        echo "[ERROR] $*" >> "$LOG_FILE" 2>/dev/null || true
    fi
}

log_debug() {
    if [[ "$VERBOSE" == "true" ]]; then
        echo -e "${BLUE}[DEBUG]${NC} $*" >&2
        if [[ -n "${LOG_FILE:-}" ]]; then
            echo "[DEBUG] $*" >> "$LOG_FILE" 2>/dev/null || true
        fi
    fi
}

# Error handling
error_exit() {
    log_error "FATAL: $1"
    cleanup_temp
    exit "${2:-1}"
}

cleanup_temp() {
    if [[ -d "$TEMP_DIR" ]]; then
        log_debug "Cleaning up temporary directory: $TEMP_DIR"
        rm -rf "$TEMP_DIR"
    fi
}

# Signal handlers
trap 'error_exit "Script interrupted by user" 130' INT TERM
trap 'cleanup_temp' EXIT

# Validation functions
validate_project_root() {
    local required_files=("version.json" "README.md" "auto_install/main.py")
    local required_dirs=("configs" "auto_install/components" "bin")
    
    log_debug "Validating project root structure"
    
    for file in "${required_files[@]}"; do
        if [[ ! -f "${PROJECT_ROOT}/${file}" ]]; then
            error_exit "Required file not found: ${file}"
        fi
    done
    
    for dir in "${required_dirs[@]}"; do
        if [[ ! -d "${PROJECT_ROOT}/${dir}" ]]; then
            # Create missing directories if they should exist
            if [[ "$dir" == "configs" ]]; then
                log_warn "Creating missing configs directory"
                mkdir -p "${PROJECT_ROOT}/$dir"
            else
                error_exit "Required directory not found: ${dir}"
            fi
        fi
    done
}

get_version_from_json() {
    if ! command -v python3 >/dev/null 2>&1; then
        error_exit "Python 3 is required but not installed"
    fi
    
    python3 -c "
import json, sys
try:
    with open('${PROJECT_ROOT}/version.json', 'r') as f:
        data = json.load(f)
    print(data['version'])
except (KeyError, FileNotFoundError, json.JSONDecodeError) as e:
    print(f'Error reading version: {e}', file=sys.stderr)
    sys.exit(1)
"
}

validate_version() {
    local version="$1"
    
    # Semantic version regex - use grep instead of bash regex for better compatibility
    if ! echo "$version" | grep -qE '^[0-9]+\.[0-9]+\.[0-9]+(-[a-zA-Z0-9.-]+)?$'; then
        error_exit "Invalid semantic version format: $version"
    fi
    
    log_debug "Version format validated: $version"
}

# Asset preparation functions
create_directory_structure() {
    local version="$1"
    local staging_dir="${TEMP_DIR}/wsl-tmux-nvim-setup-v${version}"
    
    log_info "Creating directory structure for version $version"
    
    # Create main structure
    mkdir -p "$staging_dir"/{configs,scripts/components,docs,cli}
    
    echo "$staging_dir"
}

copy_configuration_files() {
    local staging_dir="$1"
    local configs_src="${PROJECT_ROOT}"
    local configs_dest="${staging_dir}/configs"
    
    log_info "Copying configuration files"
    
    # Core configuration files
    local config_files=(
        ".bashrc"
        ".tmux.conf" 
        ".gitconfig"
        ".gitignore_global"
        "kitty.conf"
    )
    
    for config in "${config_files[@]}"; do
        if [[ -f "${configs_src}/${config}" ]]; then
            log_debug "Copying ${config}"
            cp "${configs_src}/${config}" "${configs_dest}/${config#.}"
        else
            log_warn "Configuration file not found: $config"
        fi
    done
    
    # Directory-based configurations
    local config_dirs=("yazi" "lazygit" "synth-shell")
    
    for dir in "${config_dirs[@]}"; do
        if [[ -d "${configs_src}/${dir}" ]]; then
            log_debug "Copying directory: $dir"
            cp -r "${configs_src}/${dir}" "${configs_dest}/"
        else
            log_warn "Configuration directory not found: $dir"
        fi
    done
    
    # Neovim configuration (if exists)
    if [[ -d "${configs_src}/.config/nvim" ]]; then
        mkdir -p "${configs_dest}/nvim"
        cp -r "${configs_src}/.config/nvim"/* "${configs_dest}/nvim/"
    elif [[ -d "${configs_src}/nvim" ]]; then
        cp -r "${configs_src}/nvim" "${configs_dest}/"
    fi
}

copy_installation_scripts() {
    local staging_dir="$1"
    local scripts_dest="${staging_dir}/scripts"
    
    log_info "Copying installation scripts"
    
    # Main installation system
    if [[ -d "${PROJECT_ROOT}/auto_install" ]]; then
        cp -r "${PROJECT_ROOT}/auto_install" "${staging_dir}/"
    fi
    
    # Binary scripts
    if [[ -d "${PROJECT_ROOT}/bin" ]]; then
        mkdir -p "${scripts_dest}/bin"
        cp "${PROJECT_ROOT}/bin"/*.sh "${scripts_dest}/bin/" 2>/dev/null || true
    fi
    
    # Component installation scripts
    if [[ -d "${PROJECT_ROOT}/auto_install/components" ]]; then
        cp "${PROJECT_ROOT}/auto_install/components"/*.sh "${scripts_dest}/components/" 2>/dev/null || true
    fi
    
    # Backup and restore utilities
    create_backup_script "${scripts_dest}"
    create_restore_script "${scripts_dest}"
}

create_backup_script() {
    local scripts_dest="$1"
    
    log_debug "Creating backup utility script"
    
    cat > "${scripts_dest}/backup.sh" << 'EOF'
#!/bin/bash
# WSL-Tmux-Nvim-Setup Configuration Backup Utility

set -euo pipefail

BACKUP_DIR="${HOME}/.config/wsl-setup-backup/$(date +%Y%m%d_%H%M%S)"
CONFIG_FILES=(.bashrc .tmux.conf .gitconfig .gitignore_global)
CONFIG_DIRS=(.config/nvim .config/yazi .config/lazygit)

echo "Creating backup at: $BACKUP_DIR"
mkdir -p "$BACKUP_DIR"

# Backup configuration files
for file in "${CONFIG_FILES[@]}"; do
    if [[ -f "${HOME}/${file}" ]]; then
        cp "${HOME}/${file}" "$BACKUP_DIR/"
        echo "Backed up: $file"
    fi
done

# Backup configuration directories  
for dir in "${CONFIG_DIRS[@]}"; do
    if [[ -d "${HOME}/${dir}" ]]; then
        cp -r "${HOME}/${dir}" "$BACKUP_DIR/"
        echo "Backed up: $dir"
    fi
done

echo "Backup completed successfully"
echo "Backup location: $BACKUP_DIR"
EOF
    
    chmod +x "${scripts_dest}/backup.sh"
}

create_restore_script() {
    local scripts_dest="$1"
    
    log_debug "Creating restore utility script"
    
    cat > "${scripts_dest}/restore.sh" << 'EOF'
#!/bin/bash
# WSL-Tmux-Nvim-Setup Configuration Restore Utility

set -euo pipefail

if [[ $# -eq 0 ]]; then
    echo "Usage: $0 <backup_directory>"
    echo "Available backups:"
    ls -la "${HOME}/.config/wsl-setup-backup/" 2>/dev/null || echo "No backups found"
    exit 1
fi

BACKUP_DIR="$1"

if [[ ! -d "$BACKUP_DIR" ]]; then
    echo "Error: Backup directory not found: $BACKUP_DIR"
    exit 1
fi

echo "Restoring configuration from: $BACKUP_DIR"

# Restore files
find "$BACKUP_DIR" -maxdepth 1 -type f -name ".*" | while read -r file; do
    filename="$(basename "$file")"
    echo "Restoring: $filename"
    cp "$file" "${HOME}/${filename}"
done

# Restore directories
find "$BACKUP_DIR" -maxdepth 1 -type d -name ".*" | while read -r dir; do
    dirname="$(basename "$dir")"
    target_dir="${HOME}/${dirname}"
    
    if [[ -d "$target_dir" ]]; then
        echo "Backing up existing $dirname to ${dirname}.bak"
        mv "$target_dir" "${target_dir}.bak"
    fi
    
    echo "Restoring: $dirname"
    cp -r "$dir" "$target_dir"
done

echo "Restore completed successfully"
EOF
    
    chmod +x "${scripts_dest}/restore.sh"
}

copy_documentation() {
    local staging_dir="$1"
    local docs_dest="${staging_dir}/docs"
    
    if [[ "$INCLUDE_DOCS" == "false" ]]; then
        log_info "Skipping documentation (--no-docs specified)"
        return
    fi
    
    log_info "Copying documentation"
    
    # Core documentation
    local doc_files=("README.md" "CHANGELOG.md")
    
    for doc in "${doc_files[@]}"; do
        if [[ -f "${PROJECT_ROOT}/${doc}" ]]; then
            log_debug "Copying ${doc}"
            cp "${PROJECT_ROOT}/${doc}" "${docs_dest}/"
        fi
    done
    
    # Additional documentation
    local additional_docs=("Auto-Update-Guide.md" "IMPLEMENTATION-PLAN-Release-System.md")
    
    for doc in "${additional_docs[@]}"; do
        if [[ -f "${PROJECT_ROOT}/${doc}" ]]; then
            log_debug "Copying ${doc}"
            cp "${PROJECT_ROOT}/${doc}" "${docs_dest}/"
        fi
    done
}

create_main_installer() {
    local staging_dir="$1"
    local version="$2"
    
    log_info "Creating main installer script"
    
    cat > "${staging_dir}/install.sh" << EOF
#!/bin/bash
# WSL-Tmux-Nvim-Setup v${version} - Main Installer
# Generated by prepare-release.sh on $(date -u +"%Y-%m-%d %H:%M:%S UTC")

set -euo pipefail

# Configuration
readonly VERSION="${version}"
readonly INSTALL_DIR="\${HOME}/.local/share/wsl-tmux-nvim-setup"
readonly CONFIG_BACKUP_DIR="\${HOME}/.config/wsl-setup-backup/pre-install-\$(date +%Y%m%d_%H%M%S)"

# Colors for output
readonly GREEN='\033[0;32m'
readonly YELLOW='\033[1;33m'
readonly RED='\033[0;31m'
readonly NC='\033[0m'

log_info() { echo -e "\${GREEN}[INFO]\${NC} \$*"; }
log_warn() { echo -e "\${YELLOW}[WARN]\${NC} \$*"; }
log_error() { echo -e "\${RED}[ERROR]\${NC} \$*" >&2; }

main() {
    log_info "Starting WSL-Tmux-Nvim-Setup v\${VERSION} installation"
    
    # Create backup
    if command -v ./scripts/backup.sh >/dev/null 2>&1; then
        log_info "Creating configuration backup"
        ./scripts/backup.sh
    fi
    
    # Run Python installation system
    if [[ -f "auto_install/main.py" ]]; then
        log_info "Running component installation"
        cd auto_install
        python3 main.py
        cd ..
    else
        log_error "Installation system not found"
        exit 1
    fi
    
    log_info "Installation completed successfully!"
    log_info "Version: \${VERSION}"
    
    # Source new configuration
    if [[ -f "\${HOME}/.bashrc" ]]; then
        log_info "Please run: source ~/.bashrc"
    fi
}

main "\$@"
EOF
    
    chmod +x "${staging_dir}/install.sh"
}

create_standalone_cli() {
    local staging_dir="$1"
    local version="$2"
    
    log_info "Creating standalone CLI application"
    
    # Create a placeholder CLI (full implementation would be in Phase 3)
    cat > "${staging_dir}/wsm" << EOF
#!/usr/bin/env python3
# WSL-Tmux-Nvim-Setup Manager (WSM) v${version}
# Standalone CLI application for managing installations and updates

import sys
import argparse

def main():
    parser = argparse.ArgumentParser(description='WSL-Tmux-Nvim-Setup Manager')
    parser.add_argument('--version', action='version', version='wsm ${version}')
    
    subparsers = parser.add_subparsers(dest='command')
    subparsers.add_parser('status', help='Show current installation status')
    subparsers.add_parser('update', help='Update to latest version')
    
    args = parser.parse_args()
    
    if args.command == 'status':
        print("WSM v${version}")
        print("Status: Installed")
    elif args.command == 'update':
        print("Update functionality will be available in v1.1.0")
    else:
        parser.print_help()

if __name__ == '__main__':
    main()
EOF
    
    chmod +x "${staging_dir}/wsm"
}

copy_version_info() {
    local staging_dir="$1"
    
    log_info "Copying version information"
    cp "${PROJECT_ROOT}/version.json" "${staging_dir}/"
}

create_archive() {
    local staging_dir="$1"
    local version="$2"
    local format="$3"
    
    local archive_name="wsl-tmux-nvim-setup-v${version}"
    local archive_path
    
    log_info "Creating $format archive"
    
    # Convert RELEASE_DIR to absolute path if it's relative
    local abs_release_dir
    if [[ "$RELEASE_DIR" = /* ]]; then
        abs_release_dir="$RELEASE_DIR"
    else
        abs_release_dir="$(cd "$PROJECT_ROOT" && pwd)/$RELEASE_DIR"
    fi
    
    # Ensure the release directory exists
    mkdir -p "$abs_release_dir"
    
    cd "$TEMP_DIR" || error_exit "Failed to change to temp directory"
    
    case "$format" in
        "tar.gz")
            archive_path="${abs_release_dir}/${archive_name}.tar.gz"
            tar -czf "$archive_path" "$(basename "$staging_dir")"
            ;;
        "zip")
            archive_path="${abs_release_dir}/${archive_name}.zip"
            if command -v zip >/dev/null 2>&1; then
                zip -r "$archive_path" "$(basename "$staging_dir")"
            else
                log_warn "zip command not found, skipping zip archive"
                return
            fi
            ;;
        *)
            error_exit "Unsupported archive format: $format"
            ;;
    esac
    
    if [[ -f "$archive_path" ]]; then
        local size
        size=$(du -h "$archive_path" | cut -f1)
        log_info "Created archive: $(basename "$archive_path") (${size})"
        echo "$archive_path"
    fi
}

# Usage information
usage() {
    cat << EOF
Usage: $SCRIPT_NAME [OPTIONS]

Prepare release assets for WSL-Tmux-Nvim-Setup

OPTIONS:
    -v, --version VERSION    Release version (default: auto-detect from version.json)
    -f, --format FORMAT      Archive format: tar.gz, zip, or both (default: both)
    -o, --output DIR         Output directory (default: ./release-assets)
    --no-docs               Skip documentation files
    --verbose               Enable verbose logging
    -h, --help              Show this help message

EXAMPLES:
    $SCRIPT_NAME                           # Auto-detect version, create both formats
    $SCRIPT_NAME -v 1.2.3 -f tar.gz       # Specific version, tar.gz only
    $SCRIPT_NAME --no-docs --verbose       # Skip docs, verbose output

EOF
}

# Argument parsing
parse_arguments() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            -v|--version)
                VERSION="$2"
                shift 2
                ;;
            -f|--format)
                OUTPUT_FORMAT="$2"
                shift 2
                ;;
            -o|--output)
                RELEASE_DIR="$2"
                shift 2
                ;;
            --no-docs)
                INCLUDE_DOCS="false"
                shift
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
    
    # Initialize directory and file paths after parsing arguments
    readonly TEMP_DIR="${RELEASE_DIR}/tmp"
    readonly LOG_FILE="${RELEASE_DIR}/prepare-release.log"
    
    # Setup environment
    mkdir -p "$RELEASE_DIR" "$TEMP_DIR"
    
    # Initialize logging
    cat > "$LOG_FILE" << EOF
# WSL-Tmux-Nvim-Setup Release Preparation Log
# Started: $(date -u +"%Y-%m-%d %H:%M:%S UTC")
# Script: $SCRIPT_NAME
# Project: $PROJECT_ROOT

EOF
    
    log_info "Starting release preparation"
    log_debug "Project root: $PROJECT_ROOT"
    log_debug "Release directory: $RELEASE_DIR"
    log_debug "Temporary directory: $TEMP_DIR"
    
    # Validation
    validate_project_root
    
    # Determine version
    if [[ -z "$VERSION" ]]; then
        VERSION=$(get_version_from_json)
        log_info "Auto-detected version: $VERSION"
    else
        log_info "Using specified version: $VERSION"
    fi
    
    validate_version "$VERSION"
    
    # Create staging directory
    staging_dir=$(create_directory_structure "$VERSION")
    log_debug "Staging directory: $staging_dir"
    
    # Prepare assets
    copy_configuration_files "$staging_dir"
    copy_installation_scripts "$staging_dir"
    copy_documentation "$staging_dir"
    create_main_installer "$staging_dir" "$VERSION"
    create_standalone_cli "$staging_dir" "$VERSION"
    copy_version_info "$staging_dir"
    
    # Create archives
    case "$OUTPUT_FORMAT" in
        "both")
            create_archive "$staging_dir" "$VERSION" "tar.gz"
            create_archive "$staging_dir" "$VERSION" "zip"
            ;;
        "tar.gz"|"zip")
            create_archive "$staging_dir" "$VERSION" "$OUTPUT_FORMAT"
            ;;
        *)
            error_exit "Invalid output format: $OUTPUT_FORMAT"
            ;;
    esac
    
    log_info "Release preparation completed successfully"
    log_info "Release assets created in: $RELEASE_DIR"
    
    # Summary
    echo
    echo "Release Summary:"
    echo "=================="
    echo "Version: $VERSION"
    echo "Output directory: $RELEASE_DIR"
    echo "Archives created:"
    
    find "$RELEASE_DIR" -name "*.tar.gz" -o -name "*.zip" | while read -r archive; do
        size=$(du -h "$archive" | cut -f1)
        echo "  - $(basename "$archive") (${size})"
    done
}

# Execute main function with all arguments
main "$@"
