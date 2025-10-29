#!/bin/bash

# Document Translator Installation Script

echo "======================================"
echo "Document Translator - Installation"
echo "======================================"
echo ""

# Function to check command existence
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Check Python
echo "Checking Python installation..."
if command_exists python3; then
    PYTHON_VERSION=$(python3 --version | cut -d' ' -f2)
    echo "✓ Python 3 found: $PYTHON_VERSION"
else
    echo "✗ Python 3 not found. Please install Python 3.8 or higher."
    exit 1
fi

# Check pip
echo "Checking pip installation..."
if command_exists pip3; then
    echo "✓ pip3 found"
else
    echo "✗ pip3 not found. Please install pip."
    exit 1
fi

# Install Python dependencies
echo ""
echo "Installing Python dependencies..."
pip3 install googletrans==4.0.0rc1 defusedxml --break-system-packages

if [ $? -eq 0 ]; then
    echo "✓ Python dependencies installed successfully"
else
    echo "✗ Failed to install Python dependencies"
    exit 1
fi

# Check Node.js (optional, for creating sample documents)
echo ""
echo "Checking Node.js installation (optional)..."
if command_exists node; then
    NODE_VERSION=$(node --version)
    echo "✓ Node.js found: $NODE_VERSION"
    
    # Install docx package
    echo "Installing docx package..."
    npm install docx
    
    if [ $? -eq 0 ]; then
        echo "✓ Node.js packages installed successfully"
    fi
else
    echo "⚠ Node.js not found (optional - only needed for creating sample documents)"
fi

# Test installation
echo ""
echo "Testing installation..."
python3 document_translator.py > /dev/null 2>&1

if [ $? -eq 1 ]; then
    echo "✓ Document translator is working"
else
    echo "✗ Document translator test failed"
    exit 1
fi

echo ""
echo "======================================"
echo "Installation Complete!"
echo "======================================"
echo ""
echo "Quick Start:"
echo "1. Command Line:"
echo "   python3 document_translator.py input.docx output.docx es"
echo ""
echo "2. GUI Interface:"
echo "   python3 document_translator_gui.py"
echo ""
echo "3. Create Sample Document:"
echo "   node create_sample_document.js"
echo ""
echo "For more information, see README.md"
echo "======================================"
