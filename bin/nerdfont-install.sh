#!/bin/bash

# Define the download URL
URL="https://github.com/ryanoasis/nerd-fonts/releases/download/v3.2.1/FiraCode.zip"

# Define the temporary directory where the font will be downloaded and extracted
TEMP_DIR="/tmp/firacode_font"
mkdir -p "$TEMP_DIR"

# Download the ZIP file
echo "Downloading Fira Code..."
wget -q -O "$TEMP_DIR/FiraCode.zip" "$URL"

# Check if the file was downloaded correctly
if [ ! -f "$TEMP_DIR/FiraCode.zip" ]; then
    echo "Error: The download has failed."
    exit 1
fi

# Unzip the file in the temporary directory
echo "Unzipping the font..."
unzip -q "$TEMP_DIR/FiraCode.zip" -d "$TEMP_DIR"

# Move the fonts to the system's fonts folder
echo "Installing the font on the system..."
sudo mkdir -p /usr/local/share/fonts/FiraCode
sudo cp "$TEMP_DIR"/*.ttf /usr/local/share/fonts/FiraCode/

# Clean up temporary files
echo "Cleaning up..."
rm -rf "$TEMP_DIR"

# Update the system's font cache
echo "Updating the system's font cache..."
sudo fc-cache -fv

echo "Fira Code installation has completed successfully."

