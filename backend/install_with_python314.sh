#!/bin/bash

# Installation script for Python 3.14 with forward compatibility
# This uses the stable ABI to bypass version checks

echo "🔧 Installing dependencies for Python 3.14..."
echo "⚠️  Warning: Python 3.14 is not officially supported yet."
echo "   Using ABI3 forward compatibility mode."
echo ""

# Set the forward compatibility flag
export PYO3_USE_ABI3_FORWARD_COMPATIBILITY=1

# Upgrade pip
pip install --upgrade pip

# Install packages one by one with the compatibility flag
echo "📦 Installing core packages..."

# Install packages that don't need compilation first
pip install python-dotenv python-multipart

# Install pydantic with forward compatibility
echo "📦 Installing pydantic (this may take a few minutes)..."
PYO3_USE_ABI3_FORWARD_COMPATIBILITY=1 pip install pydantic

# Install other packages
pip install fastapi uvicorn[standard]
pip install google-generativeai openai
pip install PyPDF2
pip install pytest pytest-asyncio pytest-cov httpx

echo ""
echo "✅ Installation complete!"
echo ""
echo "Note: Some features may be unstable with Python 3.14."
echo "For best compatibility, consider using Python 3.12:"
echo "  brew install python@3.12  # macOS"
echo "  pyenv install 3.12.0      # with pyenv"
