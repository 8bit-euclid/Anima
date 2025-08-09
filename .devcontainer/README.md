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

The container automatically runs `make install` which:
1. Installs the project in editable mode (`pip install -e .`)
2. Installs Blender dependencies via the custom script
3. Sets up the development environment

This means your changes to the source code are immediately available for testing.

## Testing

### Local Testing
Run tests with:
```bash
pytest
# or use make
make test
```

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
