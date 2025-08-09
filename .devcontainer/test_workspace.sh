#!/bin/bash

# Essential devcontainer test script for Anima project
echo "🧪 Testing Anima development environment..."

# Test Python and core packages
echo "Testing Python environment..."
python3 --version || { echo "❌ Python 3 not found"; exit 1; }

echo "Testing core packages..."
python3 -c "import numpy, scipy" || { echo "❌ NumPy/SciPy not available"; exit 1; }
python3 -c "import bpy" || { echo "❌ Blender Python (bpy) not available"; exit 1; }

# Test project installation
echo "Testing Anima project..."
python3 -c "import anima" || { echo "❌ Anima package not importable"; exit 1; }

# Test development tools
echo "Testing development tools..."
command -v pytest >/dev/null || { echo "❌ pytest not found"; exit 1; }
command -v make >/dev/null || { echo "❌ make not found"; exit 1; }

echo "✅ Development environment ready!"
