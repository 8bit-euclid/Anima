#!/bin/bash

# Start virtual display for headless Blender operations
# This script can be sourced or run to set up a virtual display

if [ -z "$DISPLAY" ]; then
    export DISPLAY=:99
fi

# Check if Xvfb is already running
if ! pgrep -x "Xvfb" > /dev/null; then
    echo "Starting virtual display..."
    Xvfb :99 -screen 0 1024x768x24 > /dev/null 2>&1 &
    sleep 1
    echo "Virtual display started on DISPLAY=$DISPLAY"
else
    echo "Virtual display already running on DISPLAY=$DISPLAY"
fi

# Verify X11 libraries are available
echo "Checking X11 libraries..."
if ldconfig -p | grep -q libXxf86vm.so.1; then
    echo "✓ libXxf86vm.so.1 found"
else
    echo "✗ libXxf86vm.so.1 not found"
fi

if ldconfig -p | grep -q libGL.so.1; then
    echo "✓ libGL.so.1 found"
else
    echo "✗ libGL.so.1 not found"
fi
