# Use the Python 3.11 dev container base image
FROM mcr.microsoft.com/devcontainers/python:3.11

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

# Create workspace directory
RUN mkdir -p /workspaces/anima

# Set ownership and permissions of workspace
RUN chown -R vscode:vscode /workspaces/anima \
    && chmod -R 755 /workspaces/anima

# Switch to vscode user
USER vscode
WORKDIR /workspaces/anima

# Pre-install common Python packages that are likely to be used
# The actual project dependencies will be installed when the container starts
# and the project files are volume mounted
RUN pip install --user --upgrade pip setuptools wheel