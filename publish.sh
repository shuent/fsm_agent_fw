#!/bin/bash

# Exit on error
set -e

echo "🧹 Cleaning previous builds..."
rm -rf dist/

echo "🏗 Building package..."
uv build

echo "📤 Ready to publish!"
echo "To publish to PyPI, run:"
echo "uv publish"
echo ""
echo "Or if you haven't configured a token yet, follow: https://docs.astral.sh/uv/guides/publish/"
