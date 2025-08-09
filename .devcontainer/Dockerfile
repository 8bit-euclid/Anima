# Use the Python 3.11 dev container base image
FROM mcr.microsoft.com/devcontainers/python:3.11

# Upgrade pip to latest version
RUN pip install --upgrade pip

# Install minimal dependencies to fix libXxf86vm.so.1 and libXi.so.6 errors and basic bpy functionality
RUN apt-get update && apt-get install -y \
    libxxf86vm1 \
    libgl1-mesa-glx \
    libx11-6 \
    libxi6 \
    libxkbcommon0 \
    libsm6 \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Set environment variable for software rendering (headless)
ENV LIBGL_ALWAYS_SOFTWARE=1

# Switch to vscode user early to avoid permission issues with pip cache
USER vscode

# Copy the entire source code first
COPY --chown=vscode:vscode . .

# Install package in editable mode
RUN pip install --user -e .