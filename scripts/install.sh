#!/bin/bash
# WSL-Tmux-Nvim-Setup Installation Script
# This script downloads and installs the WSL development environment setup

set -euo pipefail

# Installation metadata
readonly INSTALL_VERSION="${INSTALL_VERSION:-latest}"
readonly GITHUB_REPO="albrtbc/wsl-tmux-nvim-setup"
readonly INSTALL_DIR="${INSTALL_DIR:-$HOME/.wsl-tmux-nvim-setup}"
readonly CONFIG_DIR="${CONFIG_DIR:-$HOME/.config/wsm}"

# Color codes for output
readonly RED='\033[0;31m'
readonly GREEN='\033[0;32m'
readonly YELLOW='\033[1;33m'
readonly BLUE='\033[0;34m'
readonly NC='\033[0m'

# Logging functions
log_info() {
    echo -e "${GREEN}[INFO]${NC} $*"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $*"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $*"
}

log_debug() {
    if [[ "${VERBOSE:-false}" == "true" ]]; then
        echo -e "${BLUE}[DEBUG]${NC} $*"
    fi
}

# Error handling
error_exit() {
    log_error "$1"
    exit "${2:-1}"
}

# Check prerequisites
check_prerequisites() {
    log_info "Checking prerequisites..."
    
    # Check if running in WSL
    if ! grep -qE "(microsoft|WSL)" /proc/version 2>/dev/null; then
        log_warn "This script is designed for WSL. Proceed with caution on other systems."
    fi
    
    # Check for required commands
    local required_commands=("git" "python3" "pip3")
    for cmd in "${required_commands[@]}"; do
        if ! command -v "$cmd" &> /dev/null; then
            error_exit "Required command not found: $cmd. Please install it first."
        fi
    done
    
    # Check Python version
    local python_version
    python_version=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
    if [[ $(echo "$python_version < 3.8" | bc) -eq 1 ]]; then
        error_exit "Python 3.8 or higher is required. Found: $python_version"
    fi
    
    log_info "Prerequisites check passed"
}

# Detect latest version from GitHub
get_latest_version() {
    local api_url="https://api.github.com/repos/${GITHUB_REPO}/releases/latest"
    local version
    
    log_debug "Fetching latest version from GitHub..."
    
    if command -v curl &> /dev/null; then
        version=$(curl -s "$api_url" | grep '"tag_name"' | cut -d '"' -f 4)
    elif command -v wget &> /dev/null; then
        version=$(wget -qO- "$api_url" | grep '"tag_name"' | cut -d '"' -f 4)
    else
        error_exit "Neither curl nor wget found. Cannot fetch latest version."
    fi
    
    if [[ -z "$version" ]]; then
        error_exit "Failed to detect latest version from GitHub"
    fi
    
    echo "$version"
}

# Download release assets
download_release() {
    local version="$1"
    local temp_dir="$2"
    
    log_info "Downloading release $version..."
    
    local download_url="https://github.com/${GITHUB_REPO}/releases/download/${version}/wsl-tmux-nvim-setup-${version}.tar.gz"
    local checksums_url="https://github.com/${GITHUB_REPO}/releases/download/${version}/checksums-tar.gz.txt"
    
    # Download archive
    if command -v curl &> /dev/null; then
        curl -L -o "${temp_dir}/release.tar.gz" "$download_url" || error_exit "Failed to download release"
        curl -L -o "${temp_dir}/checksums.txt" "$checksums_url" 2>/dev/null || log_warn "Checksums file not found"
    elif command -v wget &> /dev/null; then
        wget -O "${temp_dir}/release.tar.gz" "$download_url" || error_exit "Failed to download release"
        wget -O "${temp_dir}/checksums.txt" "$checksums_url" 2>/dev/null || log_warn "Checksums file not found"
    fi
    
    # Verify checksum if available
    if [[ -f "${temp_dir}/checksums.txt" ]]; then
        log_info "Verifying checksum..."
        cd "$temp_dir"
        if command -v sha256sum &> /dev/null; then
            sha256sum -c checksums.txt --ignore-missing || error_exit "Checksum verification failed"
        else
            log_warn "sha256sum not found, skipping checksum verification"
        fi
        cd - > /dev/null
    fi
    
    log_info "Download complete"
}

# Extract and install
install_release() {
    local temp_dir="$1"
    
    log_info "Installing to $INSTALL_DIR..."
    
    # Create installation directory
    mkdir -p "$INSTALL_DIR"
    
    # Extract archive
    tar -xzf "${temp_dir}/release.tar.gz" -C "$INSTALL_DIR" --strip-components=1
    
    # Install Python dependencies
    if [[ -f "${INSTALL_DIR}/requirements.txt" ]]; then
        log_info "Installing Python dependencies..."
        pip3 install --user -r "${INSTALL_DIR}/requirements.txt"
    fi
    
    # Create configuration directory
    mkdir -p "$CONFIG_DIR"
    
    # Copy default configuration if not exists
    if [[ ! -f "${CONFIG_DIR}/config.json" ]] && [[ -f "${INSTALL_DIR}/configs/default_config.json" ]]; then
        cp "${INSTALL_DIR}/configs/default_config.json" "${CONFIG_DIR}/config.json"
        log_info "Created default configuration"
    fi
    
    # Create symlink for CLI
    local bin_dir="${HOME}/.local/bin"
    mkdir -p "$bin_dir"
    
    if [[ -f "${INSTALL_DIR}/bin/wsm" ]]; then
        ln -sf "${INSTALL_DIR}/bin/wsm" "${bin_dir}/wsm"
        log_info "Created CLI symlink: ${bin_dir}/wsm"
    fi
    
    # Ensure ~/.local/bin is in PATH
    if ! echo "$PATH" | grep -q "$bin_dir"; then
        log_warn "Add ${bin_dir} to your PATH to use the 'wsm' command"
        log_info "You can add this line to your ~/.bashrc or ~/.zshrc:"
        echo "    export PATH=\"\$PATH:${bin_dir}\""
    fi
}

# Run post-installation tasks
post_install() {
    log_info "Running post-installation tasks..."
    
    # Run auto_install if available
    if [[ -f "${INSTALL_DIR}/auto_install/main.py" ]]; then
        log_info "Running initial setup..."
        python3 "${INSTALL_DIR}/auto_install/main.py" --check || true
    fi
    
    # Display success message
    echo ""
    log_info "Installation complete!"
    echo ""
    echo "Next steps:"
    echo "  1. Add ~/.local/bin to your PATH if not already added"
    echo "  2. Run 'wsm doctor' to verify installation"
    echo "  3. Run 'wsm install --interactive' to set up your development environment"
    echo ""
    echo "For more information, visit: https://github.com/${GITHUB_REPO}"
}

# Main installation flow
main() {
    log_info "WSL-Tmux-Nvim-Setup Installer"
    log_info "=============================="
    
    # Parse command line arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            --version)
                INSTALL_VERSION="$2"
                shift 2
                ;;
            --dir)
                INSTALL_DIR="$2"
                shift 2
                ;;
            --verbose)
                VERBOSE=true
                shift
                ;;
            --help)
                echo "Usage: $0 [OPTIONS]"
                echo ""
                echo "Options:"
                echo "  --version VERSION  Install specific version (default: latest)"
                echo "  --dir PATH        Installation directory (default: ~/.wsl-tmux-nvim-setup)"
                echo "  --verbose         Enable verbose output"
                echo "  --help           Show this help message"
                exit 0
                ;;
            *)
                error_exit "Unknown option: $1"
                ;;
        esac
    done
    
    # Check prerequisites
    check_prerequisites
    
    # Determine version to install
    if [[ "$INSTALL_VERSION" == "latest" ]]; then
        INSTALL_VERSION=$(get_latest_version)
    fi
    
    log_info "Installing version: $INSTALL_VERSION"
    
    # Create temporary directory
    TEMP_DIR=$(mktemp -d)
    trap 'rm -rf "$TEMP_DIR"' EXIT
    
    # Download release
    download_release "$INSTALL_VERSION" "$TEMP_DIR"
    
    # Install release
    install_release "$TEMP_DIR"
    
    # Post-installation
    post_install
}

# Run main function
main "$@"