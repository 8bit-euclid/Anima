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

- [uv](https://docs.astral.sh/uv/) (Python package manager)
- [GNU Make](https://www.gnu.org/software/make/) (for building, testing, and running)
- [Python 3.13](https://www.python.org/downloads/) (matches the Python version bundled with Blender 5.1.2)
- [Blender](https://www.blender.org/download/) (4.0+ recommended)
- [wmctrl](https://linux.die.net/man/1/wmctrl) (Linux only; used to focus the Blender window on hot reload).
- [Visual Studio Code](https://code.visualstudio.com/) (optional, but recommended for development)

## Installation

1. **Clone the Repository**
   ```bash
   git clone https://github.com/8bit-euclid/Anima.git
   cd Anima
   ```

2. **Configure Blender Settings**

   Edit `pyproject.toml` to specify your Blender version and installation directory:

   ```toml
   [tool.blender]
   version = "4.5.3"
   install-dir = "~/Applications/blender/"
   ```

   > **Note:** Your Blender directory must follow the naming convention `blender-{version}-{platform}` (e.g., `blender-4.5.3-linux-x64`)

3. **Install the Project**
   ```bash
   make install
   ```

## Verification

After installation, verify the setup by running tests:

```bash
make test
```

## Make Targets

The project includes several make targets for common development tasks. Run `make help` to see all available targets, or use these essential commands:

| Command | Description |
|---------|-------------|
| `make help` | Show all available targets with descriptions |
| `make install` | Install the project and its dependencies |
| `make install-dev` | Install the project in development mode |
| `make install-blender-deps` | Install Blender-specific dependencies |
| `make install-system-deps` | Install required system packages (e.g. wmctrl) |
| `make run` | Run the project |
| `make test` | Run all tests |
| `make format` | Format code using black and isort |
| `make lint` | Lint the project using pylint and flake8 |
| `make clean` | Clean build artifacts and cache files |
| `make all` | Run the complete workflow (clean, format, lint, install, and test) |

## Upgrading Blender

To upgrade to a new Blender version:

1. Install the new Blender version following the naming convention
2. Update `version = "4.6.0"` in `pyproject.toml`
3. Run `make install`

The system automatically updates the `bpy` dependency and paths to match.

## Development Workflows

### Running Anima with Blender

To start Blender using the **Blender Development** extension in Visual Studio Code:

```bash
make run
```

1. Open the Anima project folder in VSCode and navigate to the `run.py` file.
2. Select **Blender: Start** from the command palette (`Ctrl+Shift+P` → "Blender: Start").
3. When prompted, select the Blender executable from your installation directory.
4. Blender will launch with the current project loaded, enabling rapid development and testing.
5. Run `anima` in Blender by selecting **Blender: Run Script** from the command palette (`Ctrl+Shift+P` → "Blender: Run Script").
6. Repeat step 5 to hot-reload recent changes into Blender.

On Linux, Anima requests NVIDIA PRIME offload for both the interactive viewport and headless EEVEE rendering.
If NVIDIA detection fails or existing GPU environment settings conflict, the launch fails rather than falling back.
To explicitly use the system graphics device instead, set `ANIMA_VIEWPORT_GPU=system`. This opt-out affects Blender
graphics, not Cycles device selection or the desktop.

## Optional: Set a Key Binding for "Blender: Run Script"

To streamline step 5, you can assign a custom key binding (e.g., `Ctrl+Shift+B`) to the **Blender: Run Script** command in VSCode:

1. Open the command palette (`Ctrl+Shift+P`) and search for "Preferences: Open Keyboard Shortcuts".
2. In the search bar, type `Blender: Run Script`.
3. Click the pencil icon next to the command and press your desired key combination (e.g. `Ctrl+Shift+B`).
4. Press **Enter** to save the key binding.

Now, you can quickly hot-reload recent changes in Blender using your chosen shortcut.

## Rendering a 4K video

`make render` renders the lesson headlessly with Cycles (OptiX GPU, 3840×2160, 60 fps) to PNG frames in `out/<name>_frames/`, then encodes `out/<name>.mp4` with ffmpeg (H.264, CRF 16, BT.709; requires `ffmpeg`).

Cycles defaults to NVIDIA OptiX, falling back to CUDA, and fails if neither is available. `DEVICE=CPU` explicitly
selects CPU rendering instead; the Linux graphics-device check still applies unless explicitly opted out. EEVEE
uses Blender's graphics device rather than the Cycles device setting.

- Frames are resumable: after a crash, overheat or Ctrl+C, re-run the same command to continue. Use `RESTART=1` after changing the scene.
- Between frames, rendering pauses while the GPU is above 83 °C and resumes at 72 °C. Per-frame time, ETA, GPU temperature and VRAM are logged.
- Options: `SCRIPT=`, `OUTPUT=out/x.mp4`, `PREVIEW=1` (1080p EEVEE), `DEVICE=CPU`, `DEPTH=16` (16-bit PNG frames), `RESTART=1`.
- `make render-frame FRAME=120` renders one test frame to check time and VRAM; `make encode FRAMES=<dir> OUTPUT=<file.mp4>` re-encodes existing frames.

## Frame dimensions and background profile

`anima.scene.profile.FRAME_16X9_V1` is the starting visual profile for a consistent series:

| Metric | Value |
|---|---:|
| Visible orthographic frame | 20 × 11.25 scene units, centered at (0, 0) |
| Background, including 0.2 units of bleed on each edge | 20.4 × 11.65 units |
| Centered safe area (5% margin on each side) | 18 × 10.125 units |
| Reference output / master | 1920 × 1080 / 3840 × 2160, square pixels, 60 fps |
| Pixels per scene unit | 96 at 1080p; 192 at 4K |
| Typography presets (TeX points) | body 10 pt, label 7.5 pt, title 15 pt |
| TeX dimension conversion | 0.08 scene units per TeX point |
| Background texture tile | 10 × 10 scene units |

These are initial design values, not verified readability limits. The visual profile is immutable and named: introduce
a new profile/version for deliberate series-wide changes, rather than silently changing the meaning of an existing
video. Preserve the font, TeX preamble, texture assets, Blender/TeX versions, render settings, and encoding settings
when reproducing a series. The profile retains its original `paper-16x9-v1` identity despite its general API name.
The default 0.015-unit curve width is about 1.44 pixels at 1080p. This also reduces defaults derived from curve width,
including point radii and arrow sizes; explicitly specified widths are unchanged.

The default demo uses `create_background` from `anima.scene.background` and `configure_lighting` and
`configure_camera` from `anima.scene.setup`. The camera helper checks the configured resolution's aspect ratio,
sets square pixels and a centered
orthographic camera at (0, 0, 10), and configures clipping. It also **reconfigures an existing active camera**;
parented, constrained or animated cameras are rejected, and render borders and depth of field are disabled.
Camera height does not control orthographic zoom. The lighting helper
creates a fixed sun and a new scene world and sets sRGB/AgX color management; call it intentionally because it
replaces the scene's world. Preview EEVEE and final Cycles are not visually identical.

`create_background(texture_dir)` loads recognized texture maps and registers the rectangle in the active scene;
`get_background()` retrieves it. Missing directories or directories without recognized maps raise an error. Clearing
the scene clears the registration; a deleted or unlinked background cannot be retrieved. Registration is
scene-specific, and registering another background replaces the active reference but does not delete the old object.
Call `object.inherit_textures_from(get_background())` to apply the current maps to an object and its descendants.
This is an explicit snapshot, not a live subscription to later background changes. The default demo applies it to
its text and curves; creating a primitive elsewhere does not implicitly apply textures.
Materials with the same texture maps and settings share a shader node group, while keeping their own color and
opacity. Editing a shared node group in Blender affects every material using it.

For ink over paper, height-based reveal is opt-in:

```python
text.inherit_textures_from(get_background(), height_reveal=(0.1, 0.9), ink_coverage=(0.2, 1.0))
text.set_material_properties(specular_ior_level=0.5)
```

`height_reveal` is an ordered pair of percentiles from 0 to 1, estimated from uniformly sampled, non-color
height-map pixels. The two `ink_coverage` values are the ink opacities below and above those thresholds;
coverage varies linearly with height between them. They default to `(0, 1)` and may be reversed. Equal
percentiles produce a hard step, with the upper coverage at the threshold. A missing height map, invalid values,
or distinct percentiles that resolve to the same sampled height raise `ValueError`. A custom link to the
material's Alpha input is also rejected rather than overwritten. Coverage multiplies the object's opacity,
so fades still work. Revealed areas show whatever is behind the object, normally the paper;
this is an opacity effect, not a physical ink-absorption simulation. Percentiles describe the whole texture,
not necessarily the part covered by a particular glyph; filtering also affects the apparent result. The sample
is cached per file and file modification metadata. Reapply textures after changing the file. Unsaved Blender
image edits must be saved or reloaded before applying height reveal. Specular response is independent of reveal; a linked
roughness map overrides a material's scalar roughness setting.

`GlyphGroup.from_tex_string(text, font_size=...)` asks LaTeX to typeset at the given base font size in TeX points,
defaulting to the profile's body size. LaTeX controls font selection, spacing, math styles, and inline size commands.
Standard named commands such as `\large` use the document class's predefined sizes; they are not necessarily
relative to the requested base size.
The profile then converts all SVG geometry and positions using the same fixed scale: 0.08 scene units per TeX point.
Thus 10 pt corresponds to a nominal 0.8 scene units, but visible glyph heights depend on the font and character.
For example:

```python
from anima.latex.glyph_group import GlyphGroup
from anima.scene.state import get_profile

profile = get_profile()

body = GlyphGroup.from_tex_string(r"$E = mc^2$")
label = GlyphGroup.from_tex_string("Radius", font_size=profile.label_font_size)
title = GlyphGroup.from_tex_string("Geometry", font_size=profile.title_font_size, with_borders=True)
custom = GlyphGroup.from_tex_string(r"Text {\large larger text}", font_size=12)
```

For custom packages, macros, or fonts, pass a reusable preamble-only `TeXDocument` as `tex_template`.
Start with `set_defaults()` to retain Anima's standalone document and default packages, then customize it:

```python
from anima.latex.tex_document import TeXDocument

template = (
    TeXDocument()
    .set_defaults()
    .add_package("mathtools")
    .add_new_command("half", r"\frac{#1}{2}")
    .set_main_font("Latin Modern Roman")
)
formula = GlyphGroup.from_tex_string(r"$\half{x}$", tex_template=template)
```

Each call copies the template before adding its body, so it can be reused. Templates with existing body content are
rejected. Templates must work with LuaLaTeX in DVI mode and dvisvgm; other compilers are not configurable.
Character labels depend on font metadata supplied by dvisvgm and may be unavailable for some fonts or expressions.
Packages, macros, and raw preamble entries are emitted in the order they are added. Adding the same package or macro
twice through the corresponding method raises `ValueError`; raw preamble entries are not checked for duplicates.
`set_main_font()` replaces its previous font and size declarations in place. The requested `font_size` on
`from_tex_string()` sets the size of the rendered body independently of the template's default font size.

For named parts, supply ordered TeX fragments to `from_tex_parts()` and retrieve a non-owning selection:

```python
equation = GlyphGroup.from_tex_parts({"left": r"$a^2+b^2", "equals": "=", "right": r"c^2$"})
left = equation.part("left")
print(left.text)
for glyph in left:
    print(glyph.name)
```

Fragments are concatenated without separators and typeset together. Each fragment must have balanced braces and
must not end with a control sequence; boundaries cannot occur inside TeX arguments, comments, verbatim content, or
macro definitions. A fragment that produces no glyphs has an empty selection. Selections are read-only snapshots of
glyph references, not groups: they do not reparent glyphs and retain their references if the group is later modified.
Fraction rules are included in selections but contribute no text.

Style a selection without affecting other glyphs, or pass it to `Stagger` to animate just those glyphs:

```python
from anima.animation.effects import Fade, Stagger

left.set_color("#c0392b").set_opacity(0.7)
reveal = Stagger(equation, children=equation.part("right"), lag_ratio=0.5, child_effect=Fade)
```

Styling also applies to glyph borders and is a no-op for empty selections. `Fade` animates opacity from 0 to 1,
replacing any previously set opacity on its selected glyphs.

Part mapping uses LuaLaTeX node attributes and post-shaping SVG markers, preserving kerning across boundaries.
`TeXPartMappingError` from `anima.latex.tex_doc_processor` is raised when a reliable mapping cannot be established,
including ligatures spanning parts, HarfBuzz-rendered fonts, unsupported SVG shapes, or multiple pages. Custom TeX
that changes syntax or interferes with the internal attribute and shipout hooks is not supported. Use
`from_tex_string()` for unrestricted TeX without part mapping.

TeX can arrange lines within a single glyph group: use `aligned` or `array` for math, and a bounded `\parbox`
for paragraph wrapping. For example:

```python
paragraph = GlyphGroup.from_tex_string(r"\parbox{3cm}{Alpha beta gamma delta epsilon zeta eta theta.}")
equations = GlyphGroup.from_tex_string(r"$\begin{aligned}a&=b\\c&=d\end{aligned}$")
```

`\parbox` widths are TeX dimensions, not scene units; TeX controls line breaks and may report overfull boxes.
Semantic parts must still respect the fragment boundary rules above.

Position one object relative to another without parenting either object:

```python
proof.next_to(statement, direction="down", gap=0.5, align="left")
# Equivalent short forms:
proof.next_to(statement, direction="D", gap=0.5, align="L")
```

`next_to` moves only the target immediately. Directions are `"right"`, `"left"`, `"up"`, and `"down"`; the default
is `"right"`. The gap between measured bounds defaults to 0.5 scene units. Cross-axis alignment defaults to `"origin"`;
use `"center"`, `"top"`, or `"bottom"` for horizontal placement, or `"center"`, `"left"`, or `"right"` for vertical
placement. The relationship is not retained: call `next_to` again after the reference or its geometry changes.

To arrange independently animatable scene objects together, use a non-owning `Layout`:

```python
from anima.layout import Layout

rows = Layout.grid([[label, equation], [other_label, other_equation]], column_gap=0.8, row_gap=0.5)
page = Layout([title, rows]).tile(direction="down", gap=0.5, align="left")
page.place_in_safe_area(anchor="top_left")
```

`tile` supports the same directions, gaps, and cross-axis alignments as `next_to`, but defaults to `"down"`.
Grid columns and rows are sized to their contents; `align_x` defaults to `"left"` and `align_y` to `"origin"`.
Horizontal alignment also supports `"right"`, `"center"`, and `"origin"`; vertical alignment supports `"top"`,
`"bottom"`, `"center"`, and `"origin"`. Origins are not necessarily text baselines. Layouts can be nested and never
reparent their objects. Placement is explicit: call `place` or `place_in_safe_area` again after changing content or
geometry.

`place(at=(x, y), anchor="center", bounds=(left, bottom, right, top))` aligns the chosen point on the layout's
measured bounds with `at` in the common parent frame; omit `bounds` for an unbounded arrangement. Anchors are
`"center"`, `"left"`, `"right"`, `"top"`, `"bottom"`, `"top_left"`, `"top_right"`, `"bottom_left"`, and
`"bottom_right"`. The default anchor is `"top_left"`. `place_in_safe_area(anchor=...)` aligns the same anchor of the
layout and the safe rectangle. It is for root-level objects, uses the active profile's centered frame, and raises if
the content does not fit rather than scaling it. It assumes the profile camera's default framing.

Direction, alignment, and anchor names are case-insensitive. Short forms can be used without imports: `"R"`, `"L"`,
`"U"`, and `"D"` for directions; `"L"`, `"R"`, `"T"`, `"B"`, and `"C"` for edge or center alignment; and `"TL"`,
`"TR"`, `"BL"`, `"BR"`, `"L"`, `"R"`, `"T"`, `"B"`, and `"C"` for anchors. `"origin"` has no short form.

Both `Layout` and `next_to` measure conservative axis-aligned bounds of mesh and curve geometry, including hidden
objects, in the common parent frame. They do not measure TeX whitespace or paragraph-box width. Objects must share a
parent; empty geometry, unsupported object types, constraints, modifiers, and non-identity parent inverses on arranged
objects are rejected. Layout does not wrap text or reflow automatically.

Glyphs are border-free by default. Set `with_borders=True` on `GlyphGroup.from_tex_string()` when the outline is
needed for display or `glyph_write_on()`. Each glyph border uses one shared material, so styling any one of its
curves styles the whole border.

For a staggered write-on across a whole group, use the standalone effect builder. It returns a `Stagger` effect;
pass that effect to an `Enter` or `Exit` action as usual. Bordered glyphs use the per-glyph `glyph_write_on()`
recipe, while borderless glyph bodies fade in over their staggered windows. No borders are created implicitly.

```python
from anima.latex.glyph_group import glyph_group_write_on

reveal = glyph_group_write_on(title, lag_ratio=0.3)
```

Generated TeX output is cached across builds under the platform's user cache directory. The cache key uses the
complete generated TeX document and Anima's TeX pipeline format; it stores the outline and text SVGs together.
It does not fingerprint installed TeX packages, fonts, external files referenced by TeX, or tool versions. Clear
the cache after changing those dependencies with `clear_tex_cache()` from
`anima.latex.tex_document_processor`, or set `ANIMA_DISABLE_TEX_CACHE=1` to disable caching. Set
`ANIMA_TEX_CACHE_DIR` to choose another cache directory. A cache hit skips TeX execution, so TeX-side effects
occur only on cache misses. Successful compiler/converter output is replayed on hits, but failures are never
cached. Time-dependent or otherwise non-deterministic TeX expressions can return previously cached output;
disable caching for those expressions. The cache is bounded to 256 MiB or 512 entries and evicts older entries;
an individual entry larger than 16 MiB is not stored.

```python
from anima.latex.tex_document_processor import clear_tex_cache

clear_tex_cache()
```

To use a different profile, call `set_profile(profile)` from `anima.scene.state` once for the active Blender scene,
before obtaining render settings or building the scene. The background, camera, lighting, text, render configuration,
and default lesson frame rate then use that scene's profile. An unconfigured scene uses `FRAME_16X9_V1`; the selection
persists when objects are cleared, across hot reloads, and when the Blender file is saved. `reset_profile()` restores
the default. Changing the profile does not update objects or render settings already created, so rebuild the scene
after a change. Individual text can still override its base `font_size` without changing the fixed conversion.

```python
from dataclasses import replace

from anima.scene.profile import FRAME_16X9_V1
from anima.scene.state import set_profile

set_profile(replace(FRAME_16X9_V1, name="my-series-v1", body_font_size=12))
```

The former per-call profile arguments on scene helpers and `from_tex_string` have been removed; configure the scene
before calling them instead.

**Migration:** `em_size` has been removed. Replace `em_size=0.8`, `0.6`, or `1.2` with the body, label, or title
font size respectively; the default profile maps these to 10, 7.5, and 15 TeX points. Unlike the old post-typesetting
scale, changing the base size now lets LaTeX select fonts and lay out math at that size, so output may differ.
Older compositions using raw dvisvgm coordinates need a profile with `tex_point_size=72 / 72.27` to reproduce that
coordinate mapping; review their font sizes and layout when migrating.

For normal lessons, leave the camera and paper fixed and transform foreground content to zoom it. To zoom the
physical sheet instead, change or animate the camera's `ortho_scale` after configuring it: the world-mapped paper
grain zooms with the content. Ensure the paper covers the complete camera path, especially when zooming out, and
choose whether foreground stroke widths and labels should scale. Changing aspect ratio needs a separate framing or
recomposition policy; the default profile rejects mismatched output dimensions.

### Calibration scene

The calibration scene includes the safe-area outline, typography at three font sizes, fractions and scripts, stroke
widths, and colors on the textured paper. Set `ANIMA_TEXTURE_DIR` to the directory containing the paper maps; if
unset, the demo uses `~/Downloads/Other_Paper_vmcmfh1n_8K_surface_ms`. For example:

```bash
make render-frame SCRIPT=scripts/calibrate_dimensions.py FRAME=1 PREVIEW=1
make render-frame SCRIPT=scripts/calibrate_dimensions.py FRAME=1
```

The first renders a 1080p EEVEE preview and the second a 4K Cycles still using the GPU by default. Pass `DEVICE=CPU`
to select the CPU for Cycles. Check the actual final render and encoded
video at delivery size and on a small display: paper visibility, fine strokes, superscripts and fraction bars also
depend on texture filtering, lighting, denoising, downsampling and compression. The explicitly selected real-TeX
integration test can be run with `uv run pytest -o addopts= tests/visual_tests/test_dimensions.py` when LuaLaTeX, dvisvgm and
the configured fonts are installed.

## Curve width profiles

Curves can have independent opacity and bump-height profiles across their width:

```python
import math

curve.set_width_profile(
    opacity=lambda u: u,
    height=lambda u: 0.02 * math.sin(math.pi * u),
    samples=256,
)
curve.clear_width_profile()
```

`u` runs from the left edge (0) to the right edge (1), looking along the curve. Width and bias do not change this
normalized coordinate. Functions are sampled uniformly and linearly interpolated; increase `samples` for fine
detail. Opacity must be finite and in [0, 1], and multiplies both object opacity and texture-based ink coverage.
Height is a finite signed value in scene units, used for bump shading rather than geometric displacement. The bump
composes with existing paper texture normals. `Fade` continues to control the overall opacity.

Profiles propagate to chains, joints, dashes, and endcaps. Endcaps use the curve's width to project the profile
across their local width; shapes wider than the curve use the nearest edge value outside that width. Existing
custom Alpha or Normal shader links cannot be replaced. Curves sharing a material share its profile, and their
existing endcaps follow changes and removal. Copied curves and their endcaps remain independent of the original.
The profile is stored in a packed floating-point image so it is retained in saved Blender scenes.
Endcaps with separate materials use a dedicated UV layer; an endcap sharing its curve's material uses and
overwrites its `UVMap` layer.

To render a gallery with Cycles on the GPU:

```bash
uv run python -m tests.visual_tests.test_curve_profiles out/curve_profiles.png
```

### Approximate boundary bleed

Apply an opacity fade to a closed curve boundary in place:

```python
from anima.primitives.curve_bleed import apply_bleed

apply_bleed(boundary, width=0.1, bias=0.99)
boundary.layer = -1
```

The filled interior must be to the left of each contour: outer contours are counterclockwise and holes
clockwise in Blender coordinates. For glyphs, create them with `with_border=True` and apply the function to
each loop in `glyph.border.subpaths`. Contours with the opposite winding must be reversed before use.
Style the boundary to match the fill. Winding and planarity are not checked.

`width` is the outward fade distance in boundary-local units. `bias` is configurable in (-1, 1] and defaults
to 0.99, giving a small inward overlap; 0 gives equal inward and outward widths, and 1 gives no inward
overlap. The total curve width is `2 * width / (1 + bias)`. Opacity is constant over the interior portion
and fades linearly to 0 over the outward distance, multiplied by material opacity and texture coverage.
Scaling can change the world-space width.

This replaces the loop's width, bias, and width profile and disables shadow casting on its curve parts and
endcaps. The loop retains its parent, transforms, and reveal behavior. Profile changes affect all objects
sharing its materials; loops sharing a material should use the same bias and be styled consistently. Place the boundary below the
body and any background on a still lower layer to avoid coplanar overlap. The inward overlap can hide small
discrepancies between the boundary and fill but cannot fix every mismatch. Separate curve segments can leave
gaps at corners or overlap and darken; this is not a nearest-distance effect.

To render a glyph and polygon comparison with Cycles on the GPU:

```bash
uv run python -m tests.visual_tests.test_curve_bleed out/curve_bleed.png
```

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

## Animating objects with effects

An `Effect` maps a progress value to changes in geometry, material, transforms, or other state. Objects do not choose
default effects; actions require the user to select an effect explicitly. Effects can be composed with `Together`,
`Stagger`, and `Phase`. The action owns the duration and F-curve, while the effect defines what happens as progress
changes.

Specify durations and elapsed times as numbers of seconds (including fractional seconds), or keep using clock strings
or `timedelta` values when they are more readable.

```python
from anima.animation.action import Enter, Exit, FCurvePreset
from anima.animation.effects import Draw, Fade, Scale, Stagger, Together
from anima.animation.scheduler import Scheduler

scheduler = Scheduler()
effect = Together(group, [Fade(group), Scale(group, from_scale=0.5)])
enter = scheduler.add(
    effect,
    4,
    preset=FCurvePreset.EASE_IN_OUT,
)
# Starts at 00:00; returns the Action so its F-curve can be edited.
scheduler.wait(2)
scheduler.add_action(Exit(Together(group, [Fade(group), Scale(group)]), 1))  # starts at 00:06

# Run in parallel: either as one group, or by starting with the previous placement.
# The cursor moves to whichever placement ends last.
scheduler.add_actions(
    Enter(Draw(a), 1),
    Enter(Stagger(b, lag_ratio=0.3, child_effect=Draw), 2),
)
scheduler.add_action(Enter(Draw(c), 3), with_previous=True)
print(scheduler.end_time)  # 00:10

# A reusable, explicit recipe is provided for glyph write-on animation.
from anima.latex.glyph import glyph_write_on

glyph_effect = glyph_write_on(glyph)
scheduler.add_action(Enter(glyph_effect, "00:02"))

# The underlying F-curve is available for further editing in Python or Blender.
fcurve = enter.track.fcurve
```

Custom behaviour uses the same mechanism. A callback is a function of progress `u` (0 to 1, eased) and/or the elapsed
time `t` (a `timedelta` since the outer action started) over a window. Compositions remap `u` for their child windows
but preserve `t`. It runs only while the window is active, plus once on each side so the state is correct when scrubbing,
and is placed at the cursor like any action. It works directly or as a decorator, and
`add_callback(..., with_previous=True)` runs it alongside the previous placement.

```python
@scheduler.add_callback(duration=2)
def draw(u):
    curve.param_1 = u
```

The scheduler samples each F-curve at the incoming frame before Blender evaluates properties, so changes appear in
renders. `KeyframedProperty` is the low-level, frame-based building block exposing the driver Empty, F-curve, and
custom-property value; additional keyframes can be inserted with `track.add_keyframe(...)`. `Scheduler().reset()` clears
the schedule and cursor.
An RGBA color's alpha is the material opacity; use RGB when changing color without changing opacity.
See `tests/visual_tests/test_reveals.py` and `tests/animation/test_effect.py` for examples.

## Status

This project is a work in progress. Usage instructions and examples will be sporadically added as development progresses.

---
