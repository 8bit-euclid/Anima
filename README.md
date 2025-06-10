ANIMA

# Anima - Blender Python Animation Framework

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

### 2. Set Up Your Development Environment

- Install the **Blender Development** extension in Visual Studio Code.
- Configure the Blender executable path in VSCode settings.

### 3. Build the Project

```bash
make build
```

### 4. Run Tests

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

## Status

This project is a work in progress. Usage instructions and examples will be added as development continues.

---