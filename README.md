ANIMA

# Anima

**Anima** is a Python framework for Blender focused on mathematical visualizations, procedural animations, and educational content. It provides tools for animating curves, rendering LaTeX text, managing scenes, and supporting a streamlined development workflow.

## Features

- Tools for animating curves, splines, and geometric objects
- LaTeX text rendering as animated 3D glyphs
- Bézier spline and curve utilities
- Automated scene setup and cleanup
- Hot reload support for rapid development

## Prerequisites

- [GNU Make](https://www.gnu.org/software/make/) (for building and testing)
- [Python 3.11+](https://www.python.org/downloads/) (specifically 3.11.4 - 3.11.13 for Blender compatibility)
- [Blender](https://www.blender.org/download/) (4.0+ recommended)
- [Visual Studio Code](https://code.visualstudio.com/) with [Dev Containers extension](https://marketplace.visualstudio.com/items?itemName=ms-vscode-remote.remote-containers) (optional, for DevContainer development)

## Installation

You can set up Anima in two ways: using a DevContainer (recommended for consistent development environment) or local installation.

### Option 1: DevContainer Setup (Recommended)

The DevContainer provides a pre-configured Python 3.11 environment with all dependencies.

1. **Clone the Repository**
   ```bash
   git clone https://github.com/8bit-euclid/Anima.git
   cd Anima
   ```

2. **Open in DevContainer**
   - Open the project in Visual Studio Code
   - When prompted, click "Reopen in Container" or use `Ctrl+Shift+P` → "Dev Containers: Reopen in Container"
   - The environment will automatically install all dependencies

3. **Enter DevContainer from Terminal** (Alternative)
   ```bash
   make enter-devcontainer
   ```

### Option 2: Local Installation

1. **Clone the Repository**
   ```bash
   git clone https://github.com/8bit-euclid/Anima.git
   cd Anima
   ```

2. **Set the Blender Python path**

Ensure you have the Blender Python executable available. This is located in the Blender installation directory, e.g. `blender/4.x/python/bin/python3.x`. In the `pyproject.toml` file, set the `root-dir` under the `[tool.blender]` section to your Blender directory:

```toml
[tool.blender]
root-dir = "/path/to/blender/directory"
```

> **Note:** Unless renamed, the Blender directory will be akin to `blender-4.3.2-linux-x64` on Linux.

3. **Install the Project**
   ```bash
   make install
   ```

   > **Note:** If you add or change dependencies in `pyproject.toml`, you must run `make install` again. This ensures that the dependencies are installed in Blender's Python environment as well.

## Verification

After installation (either method), verify the setup by running tests:

```bash
make test
```

## Make Targets

The project includes several make targets for common development tasks. Run `make help` to see all available targets, or use these essential commands:

| Command | Description |
|---------|-------------|
| `make help` | Show all available targets with descriptions |
| `make install` | Install the project and its dependencies |
| `make install-blender-deps` | Install Blender-specific dependencies |
| `make enter-devcontainer` | Build and run the DevContainer |
| `make run` | Run the project |
| `make test` | Run all tests |
| `make fmt` | Format code using black and isort |
| `make lint` | Lint the project using flake8 and pylint |
| `make clean` | Clean build artifacts and cache files |
| `make all` | Run the complete workflow (clean, format, lint, test, build) |

## Development Workflows

### DevContainer Development

If you're using the DevContainer setup, you have a consistent Python 3.11 environment with all dependencies pre-installed. The DevContainer automatically:

- Installs the project in editable mode
- Sets up development tools (black, isort, pylint, pytest)
- Provides a clean, reproducible environment

You can validate the DevContainer setup by running:
```bash
bash .devcontainer/test_workspace.sh
```

### Running Anima with Blender

To start Blender using the **Blender Development** extension in Visual Studio Code:

```bash
make run
```

1. Open the Anima project folder in VSCode and navigate to the `run.py` file.
2. Select **Blender: Start** from the command palette (`Ctrl+Shift+P` → "Blender: Start").
3. When prompted, select the Blender executable (e.g., `~/applications/blender/blender-4.3.2-linux-x64/blender` on Linux).
4. Blender will launch with the current project loaded, enabling rapid development and testing.
5. Run `anima` in Blender by selecting **Blender: Run Script** from the command palette (`Ctrl+Shift+P` → "Blender: Run Script").
6. Repeat step 5 to hot-reload recent changes into Blender.

## Optional: Set a Key Binding for "Blender: Run Script"

To streamline step 5, you can assign a custom key binding (e.g., `Ctrl+Shift+B`) to the **Blender: Run Script** command in VSCode:

1. Open the command palette (`Ctrl+Shift+P`) and search for "Preferences: Open Keyboard Shortcuts".
2. In the search bar, type `Blender: Run Script`.
3. Click the pencil icon next to the command and press your desired key combination (e.g. `Ctrl+Shift+B`).
4. Press **Enter** to save the key binding.

Now, you can quickly hot-reload recent changes in Blender using your chosen shortcut.

## Logging

Anima includes a built-in logging system powered by [loguru](https://loguru.readthedocs.io/) that provides structured, colorized output for debugging and monitoring.

### Configuration

The logger can be configured using environment variables:

- `ANIMA_LOG_LEVEL`: Set the logging level (default: `DEBUG`)
  - Options: `TRACE`, `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`
- `ANIMA_LOG_SHOW_FUNCTION`: Show function names in logs (default: `0`)
  - Set to `1` to enable
- `ANIMA_LOG_SHOW_PROCESS`: Show process and thread IDs (default: `0`)
  - Set to `1` to enable

### Usage

Import and use the logger in your code:

```python
from anima.diagnostics import logger, format_output

# Basic logging examples
logger.trace("This is a trace message")
logger.info("Animation started")
logger.debug("Processing curve data")
logger.warning("Texture not found, using default")
logger.error("Failed to load mesh")

# Format output with title
output = format_output("Render Settings", "Resolution: 1920x1080\nSamples: 128")
logger.info(output)
```

To configure logging behavior, set the environment variables before running Anima.

On **Linux/macOS**:

```bash
export ANIMA_LOG_LEVEL=INFO
export ANIMA_LOG_SHOW_FUNCTION=1
make run
```

Alternatively, set them immediately before the run command:

```bash
ANIMA_LOG_LEVEL=INFO ANIMA_LOG_SHOW_FUNCTION=1 make run
```

## Status

This project is a work in progress. Usage instructions and examples will be sporadically added as development progresses.

---
