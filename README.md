# eli_lab Pattern Generator

A small procedural graphics workstation for generating abstract patterns from a deterministic seed. The current application uses **PySide6** for the desktop UI and **Pillow** for raster rendering, with optional OpenSimplex noise for flow-field distortion.

> Part of the **ELI LAB** creative-coding toolkit by Ilya Minin (Eli).

## What it does

- Generates layered abstract compositions from a seed.
- Mixes blocks, circles, lines and triangles on a configurable grid.
- Uses noise-driven flow lines and positional distortion.
- Supports `none`, `mirror`, `radial` and `grid` symmetry.
- Includes random, pastel, neon, earth and monochrome palettes.
- Renders a large PNG while keeping the UI responsive in a background worker.
- Exports a real SVG composition, not just an SVG wrapper around the raster image.
- Saves and restores generator settings as JSON presets.
- Remembers the window geometry between launches.

## Requirements

Python **3.10+** and a desktop environment supported by Qt 6.

PySide6 is the official Qt-for-Python binding and is installed from PyPI; this project therefore uses Qt 6 rather than the original Tkinter UI.

## Install

Create a virtual environment and install the project in editable mode:

```bash
python -m venv .venv

# Windows
.venv\\Scripts\\activate

# Linux / macOS
source .venv/bin/activate

python -m pip install -U pip
python -m pip install -e .
```

The project declares these runtime dependencies:

- `PySide6>=6.10`
- `Pillow>=11.0`
- `opensimplex>=0.4`

## Run

After installation:

```bash
eli-pattern-generator
```

Or directly from the repository:

```bash
python -m pattern_app.main
```

## Controls

### Core

**Canvas** controls the output size, seed, background, palette and symmetry. A fixed seed makes the procedural result reproducible. Leaving the seed empty creates a new seed for each generation.

**Generation** controls density, complexity and grid size. Auto Preview debounces changes so moving a control does not immediately launch a render for every intermediate value.

### Shapes

Enable the primitives you want the generator to choose from. Disabling everything falls back to blocks so the canvas never becomes empty by accident.

### Noise

The noise field affects both flow lines and shape positions. Scale controls spatial frequency, amplitude controls displacement, and octaves add detail at multiple frequencies.

### Effects

Enable the background gradient, accent marks, and raster blur. Blur is deliberately a raster finishing effect; SVG export remains vector-based.

### Export

PNG exports the current raster render. SVG exports the procedural vector geometry used by the composition. Presets are plain JSON and can be versioned with the project.

## Architecture

```text
pattern_app/
├── __init__.py
├── generator.py      # Pure procedural renderer + SVG generation
└── main.py           # PySide6 application and controls

tests/
└── test_generator.py
```

The renderer is intentionally independent from Qt. This makes it possible to test generation without starting a GUI and leaves room for future front ends or batch-generation tools.

## Development

Run the tests with:

```bash
python -m pytest
```

The current test suite checks color parsing, deterministic seeded output, SVG generation, and configuration normalization.

## Historical versions

`Versions/v_1`, `Versions/v_2` and `Versions/v_3` are retained as a development archive. The supported application entry point is now `pattern_app.main`.

## Roadmap

The codebase is intentionally set up for further creative expansion: more primitives, richer palettes, additional symmetry modes, parameterized layer stacks, batch rendering, and preset libraries can be added without tying the renderer to the GUI.

## Notes on the Qt migration

The old implementation was a Tkinter/Pillow monolith. The current implementation moves to PySide6, isolates the renderer, adds responsive rendering, and makes SVG export first-class.
