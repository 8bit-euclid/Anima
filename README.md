ANIMA

# Anima

**Anima** is a Python framework for Blender focused on mathematical visualizations, procedural animations, and educational content. It provides tools for animating curves, rendering LaTeX text, managing scenes, and supporting a streamlined development workflow.

## Features

- Tools for animating curves, splines, and geometric objects
- LaTeX text rendering as animated 3D glyphs
- Advanced Bézier spline and curve utilities
- Automated scene setup and cleanup
- Hot reload support for rapid development

## Prerequisites

- [GNU Make](https://www.gnu.org/software/make/) (for building and testing)
- [Python 3.10+](https://www.python.org/downloads/)
- [Blender](https://www.blender.org/download/) (4.0+ recommended)
- [Visual Studio Code](https://code.visualstudio.com/)

## Installation

### 1. Clone the Repository

```bash
git clone https://github.com/8bit-euclid/Anima.git
cd Anima
```

### 2. Set the Blender Python path

Ensure you have the Blender Python executable available. This is located in the Blender installation directory, e.g. `blender/4.x/python/bin/python3.x`. In the `pyproject.toml` file, set the `root-dir` under the `[tool.blender]` section to your Blender directory:

```toml
[tool.blender]
root-dir = "/path/to/blender/directory"
```

> **Note:** Unless renamed, the Blender directory will be akin to `blender-4.3.2-linux-x64` on Linux.

### 3. Install the Project

```bash
make install
```

> **Note:** If you add or change dependencies in `pyproject.toml`, you must run `make install` again. This ensures that the dependencies are installed in Blender's Python environment as well.

### 5. Run Tests

Verify the installation by running:

```bash
make test
```

## Running Anima with Blender

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
- `ANIMA_LOG_SHOW_PROCESS_INFO`: Show process and thread IDs (default: `0`)
  - Set to `1` to enable

### Usage

Import and use the logger in your code:

```python
from anima.diagnostics import logger

# Basic logging examples
logger.trace("This is a trace message")
logger.info("Animation started")
logger.debug("Processing curve data")
logger.warning("Texture not found, using default")
logger.error("Failed to load mesh")

# Format output with title
from anima.diagnostics import format_output
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
