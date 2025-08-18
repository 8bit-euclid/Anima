# Anima DevContainer

This DevContainer provides a pre-configured development environment for the Anima project with automatic dependency installation and development tools setup.

## Container Features

- **Python 3.11 Environment**: Pre-installed with Blender-compatible Python version
- **VS Code Extensions**: Python development tools, Makefile support
- **Automatic Setup**: Project installed in editable mode on container start
- **Development Tools**: Black, isort, pylint, pytest pre-configured

## Using the DevContainer

### VS Code Integration
- Open project in VS Code
- Click "Reopen in Container" when prompted
- Or use `Ctrl+Shift+P` → "Dev Containers: Reopen in Container"

### Terminal Access
```bash
make enter-devcontainer
```

## Container Setup

The container automatically:
- Installs project dependencies from `pyproject.toml`
- Sets up the project in editable mode
- Configures development tools (black, isort, pylint, pytest)

Changes to source code are immediately available without reinstallation.

## DevContainer Validation

Test that the container is working correctly:
```bash
bash .devcontainer/test_workspace.sh
```

This validates:
- Python 3.11 availability
- Essential packages (bpy, numpy, scipy, pytest)
- Project installation and importability
- Development tools functionality

## CI Integration

GitHub Actions workflows test the DevContainer:
- `.github/workflows/test_devcontainer.yml` - Container functionality
- `.github/workflows/build_devcontainer.yml` - Container build process

## Troubleshooting

**Container build fails**: Check Docker is running and disk space
**Dependencies missing**: Rebuild container (`Ctrl+Shift+P` → "Dev Containers: Rebuild Container")
**Environment issues**: Run the validation script to diagnose problems
