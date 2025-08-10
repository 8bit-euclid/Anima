# Anima Development Container

This devcontainer provides a Python 3.11 development environment specifically configured for the Anima project - a Blender-based animation library.

## Features

- **Python 3.11**: Matches the required Python version for Blender compatibility
- **Pre-configured Extensions**: 
  - Python development tools (pylint, black formatter, isort)
  - Makefile tools
- **Auto-setup**: Automatically installs the project in development mode
- **Testing**: Pre-configured pytest support

## Getting Started

1. Open this project in VS Code
2. When prompted, reopen in container
3. The environment will automatically install dependencies
4. You can start developing immediately!

## Project Structure

The container automatically installs the project during build:
1. Installs the project in editable mode (`pip install -e .`) with all dependencies
2. Sets up the development environment with Python 3.11

This means your changes to the source code are immediately available for testing.

## Manual Installation Commands

If you need to reinstall or work with Blender integration:

```bash
# Install the project in editable mode (already done automatically)
make install

# Install dependencies into your local Blender installation
make install-blender-deps
```

**Note**: `make install-blender-deps` requires:
- A local Blender installation (configured in `pyproject.toml` under `[tool.blender]`)
- The Blender Python executable to be accessible
- This installs anima's dependencies (bpy, numpy, scipy, etc.) into Blender's Python environment

## Testing

### Local Testing
Run tests with:
```bash
pytest
# or use make
make test
```

### Available Make Targets
- `make install`: Install the project in editable mode
- `make install-blender-deps`: Install dependencies into Blender's Python environment
- `make run`: Run the main application (`python run.py`)
- `make test`: Run tests with pytest

### DevContainer Validation
To test that the devcontainer is working correctly:
```bash
bash .devcontainer/test-workspace.sh
```

This script validates:
- Python 3.11 availability
- Essential packages (bpy, numpy, scipy)
- Project installation and importability
- pytest functionality
- Make targets
- Development tools

### CI/CD Testing
The project includes a GitHub Actions workflow (`.github/workflows/devcontainer.yml`) that automatically tests the devcontainer setup on every push and pull request. This ensures the development environment remains consistent and functional.

The container is configured to recognize the `tests/` directory and exclude visual tests by default.
