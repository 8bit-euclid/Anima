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
- [Blender](https://www.blender.org/download/) (4.0+ recommended)
- [Visual Studio Code](https://code.visualstudio.com/)
- [Blender Development Extension](https://marketplace.visualstudio.com/items?itemName=JacquesLucke.blender-development)

## Installation

### 1. Clone the Repository

```bash
git clone https://github.com/8bit-euclid/Anima.git
cd Anima
```

### 2. Install the Blender Development Extension in VSCode

### 3. Set the Blender Python path

Ensure you have the Blender Python executable available. This is located in the Blender installation directory, e.g. `blender/4.x/python/bin/python3.x`. Open the `pyproject.toml` file and set the `python_path` under the `[tool.blender]` section to your Blender Python executable. For example:

```toml
[tool.blender]
python_path = "/path/to/blender/python"
```

### 4. Build the Project

### 4. Install Blender Dependencies
The same dependencies are used for both the Blender Python environment and the Anima development environment. To install the required dependencies in the former, run:

```bash
make install-blender-deps
```

> **Note:** If you add or change dependencies in `pyproject.toml`, you must run `make install-blender-deps` again.

### 5. Run Tests

Verify the installation by running:

```bash
make test
```

## Running Anima with Blender

To start Blender using the **Blender Development** extension in Visual Studio Code:

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

## Status

This project is a work in progress. Usage instructions and examples will be added as development continues.

---
