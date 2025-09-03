#!/bin/bash
# Update from GitHub releases
# This script downloads and applies the latest release

REPO="albrtbc/wsl-tmux-nvim-setup"
API_URL="https://api.github.com/repos/$REPO/releases/latest"
TEMP_DIR="/tmp/wsl-tmux-nvim-release-update"
VERSION_FILE="$HOME/.config/wsl-tmux-nvim-setup/current-version"

cleanup() {
    rm -rf "$TEMP_DIR"
}

trap cleanup EXIT INT TERM

get_latest_release() {
    echo "Checking latest release..."
    
    # Get latest release info using GitHub API
    if command -v gh >/dev/null 2>&1; then
        # Use GitHub CLI if available
        RELEASE_INFO=$(gh api repos/$REPO/releases/latest 2>/dev/null)
    else
        # Fallback to curl
        RELEASE_INFO=$(curl -s "$API_URL" 2>/dev/null)
    fi
    
    if [ -z "$RELEASE_INFO" ]; then
        echo "Error: Could not fetch release information"
        return 1
    fi
    
    # Extract tag name and download URL
    LATEST_VERSION=$(echo "$RELEASE_INFO" | grep -o '"tag_name": *"[^"]*"' | cut -d'"' -f4)
    DOWNLOAD_URL=$(echo "$RELEASE_INFO" | grep -o '"tarball_url": *"[^"]*"' | cut -d'"' -f4)
    
    if [ -z "$LATEST_VERSION" ] || [ -z "$DOWNLOAD_URL" ]; then
        echo "Error: Could not parse release information"
        return 1
    fi
    
    echo "Latest version: $LATEST_VERSION"
    return 0
}

check_current_version() {
    if [ -f "$VERSION_FILE" ]; then
        CURRENT_VERSION=$(cat "$VERSION_FILE")
        echo "Current version: $CURRENT_VERSION"
        
        if [ "$CURRENT_VERSION" = "$LATEST_VERSION" ]; then
            echo "Already up to date!"
            return 1
        fi
    else
        echo "No version file found, assuming first install"
        CURRENT_VERSION="none"
    fi
    
    return 0
}

download_release() {
    echo "Downloading release $LATEST_VERSION..."
    
    mkdir -p "$TEMP_DIR"
    cd "$TEMP_DIR"
    
    # Download and extract the release
    if command -v gh >/dev/null 2>&1; then
        gh repo clone "$REPO" . -- --depth 1 --branch "$LATEST_VERSION"
    else
        curl -L "$DOWNLOAD_URL" -o release.tar.gz
        tar -xzf release.tar.gz --strip-components=1
    fi
    
    if [ $? -ne 0 ]; then
        echo "Error: Failed to download release"
        return 1
    fi
    
    echo "Download completed"
    return 0
}

apply_update() {
    echo "Applying update from $CURRENT_VERSION to $LATEST_VERSION..."
    
    # Use the main update script logic but from the release
    if [ -f "$TEMP_DIR/bin/update.sh" ]; then
        # Run the update script from the release
        bash "$TEMP_DIR/bin/update.sh"
    else
        echo "Error: Update script not found in release"
        return 1
    fi
    
    # Record the new version
    mkdir -p "$(dirname "$VERSION_FILE")"
    echo "$LATEST_VERSION" > "$VERSION_FILE"
    
    echo "Update completed successfully!"
    return 0
}

show_changelog() {
    if [ -f "$TEMP_DIR/CHANGELOG.md" ]; then
        echo ""
        echo "=== CHANGELOG ==="
        head -20 "$TEMP_DIR/CHANGELOG.md"
        echo "=================="
    elif command -v gh >/dev/null 2>&1; then
        echo ""
        echo "=== RELEASE NOTES ==="
        gh api repos/$REPO/releases/latest --jq '.body' | head -10
        echo "======================"
    fi
}

main() {
    echo "WSL-Tmux-Nvim-Setup Release Updater"
    echo "===================================="
    
    # Get latest release info
    if ! get_latest_release; then
        exit 1
    fi
    
    # Check if we need to update
    if ! check_current_version; then
        exit 0
    fi
    
    # Ask for confirmation unless --yes is passed
    if [ "$1" != "--yes" ]; then
        echo ""
        echo "Update from $CURRENT_VERSION to $LATEST_VERSION?"
        echo -n "Continue? (y/N): "
        read -r response
        if [[ ! "$response" =~ ^[Yy]$ ]]; then
            echo "Update cancelled"
            exit 0
        fi
    fi
    
    # Download and apply update
    if download_release && apply_update; then
        show_changelog
        echo ""
        echo "✅ Successfully updated to version $LATEST_VERSION"
        echo "🔄 Please restart your terminal or source ~/.bashrc"
    else
        echo "❌ Update failed"
        exit 1
    fi
}

# Parse arguments
case "${1:-}" in
    --check)
        get_latest_release && check_current_version
        exit $?
        ;;
    --yes)
        main --yes
        ;;
    --help|-h)
        echo "Usage: $0 [OPTIONS]"
        echo "Options:"
        echo "  --check       Check for updates without applying"
        echo "  --yes         Apply updates without confirmation"
        echo "  --help, -h    Show this help"
        exit 0
        ;;
    *)
        main "$@"
        ;;
esac