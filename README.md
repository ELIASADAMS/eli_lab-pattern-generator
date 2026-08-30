# eli_lab Pattern Generator

A procedural graphics workstation for generating abstract images and SVG compositions from a deterministic seed.

**Author / creative project:** Ilya Minin (Eli) — **eli_lab**

> The project is **eli_lab**. It is not named “ELI LAB”.

## What it does

The generator builds compositions from interacting systems instead of a single randomness slider. A pattern is the result of spatial composition, a shared vector field, weighted primitives, color behavior, layered depth, and controlled mutation.

The desktop application uses **PySide6** for the UI, **Pillow** for raster output, and OpenSimplex when available for noise-driven fields.

### Core capabilities

- Deterministic seed-based generation.
- PNG and procedural SVG export.
- Responsive background rendering through a Qt worker pool.
- JSON preset save/load.
- Persistent window geometry.
- Blocks, circles, lines, and triangles with independent probability weights.
- `none`, `mirror`, `radial`, and `grid` symmetry.
- Multiple spatial composition modes and explicit focal-point control.
- Noise, swirl, vortex, waves, and radial vector fields.
- Palette families: random, pastel, neon, earth, monochrome, ice, and ritual.
- Aspect-aware geometry for square, portrait, landscape, ultrawide, and custom canvases.

## Requirements

Python **3.10+** and a desktop environment supported by Qt 6.

Runtime dependencies are listed in `pyproject.toml` and `requirements.txt`:

- `PySide6>=6.10`
- `Pillow>=11.0`
- `opensimplex>=0.4`

Development and release dependencies are listed in `requirements-dev.txt` and include PyInstaller.

## Install

```bash
python -m venv .venv

# Windows
.venv\\Scripts\\activate

# Linux / macOS
source .venv/bin/activate

python -m pip install -U pip
python -m pip install -r requirements.txt
```

For editable development:

```bash
python -m pip install -e .
```

## Run

Recommended from the repository root:

```bash
python run.py
```

PyCharm can use the shared `eli_lab Pattern Generator` run configuration in `.idea/runConfigurations/Pattern_Generator.xml`.

Other supported forms:

```bash
python -m pattern_app.main
```

```bash
eli-pattern-generator
```

## Build the Windows application

The repository contains a dedicated PyInstaller setup in `release/` for producing a **single-file Windows x64 executable**. The tracked application icon is `Icon/favicon.ico`.

### One-command build

From the repository root, with the project `.venv` available:

```powershell
powershell -ExecutionPolicy Bypass -File .\\release\\build-windows.ps1
```

The script installs the release toolchain, runs the tests, cleans previous PyInstaller output, and builds exactly one application file:

```text
dist\\eli_lab-pattern-generator.exe
```

The executable is a PyInstaller **one-file** bundle. End users do not need Python, PySide6, Pillow, or OpenSimplex installed separately.

### Direct PyInstaller command

You can also build from PyCharm's terminal:

```powershell
python -m PyInstaller --noconfirm --clean release\\eli_lab_pattern_generator.spec
```

The executable will be at:

```text
dist\\eli_lab-pattern-generator.exe
```

The spec uses `run.py` as the frozen entry point. This avoids package-relative import failures that can occur when PyInstaller executes `pattern_app/main.py` directly as `__main__`.

Do not commit `build/`, `dist/`, or generated release artifacts.

## Release process

1. Update the version in `pyproject.toml`.
2. Update `CHANGELOG.md`.
3. Run `release/build-windows.ps1` and launch the resulting `.exe` to test it on Windows.
4. Create a Git tag matching the package version, for example:

```powershell
git tag v2.1.0
git push origin v2.1.0
```

5. Upload `dist/eli_lab-pattern-generator.exe` to the GitHub Release.

The GitHub Actions release workflow follows the same one-file Windows build and publishes the executable together with the Python package artifacts.

## Presets

Presets are ordinary JSON files containing the full `PatternConfig`. They are intended to be portable, diffable, and version-controllable.

## Architecture

```text
pattern_app/
├── __init__.py
├── generator.py        # Procedural renderer + SVG generator
├── main.py             # Stable application entry point
└── ui.py               # PySide6 editor UI

run.py
requirements.txt
requirements-dev.txt
pyproject.toml
release/
├── eli_lab_pattern_generator.spec
└── build-windows.ps1
scripts/
└── build-release.ps1
Icon/
└── favicon.ico

.github/workflows/
└── release.yml

tests/
└── test_generator.py
```

The renderer is deliberately independent of Qt. It can generate a raster image and SVG from `PatternConfig` without starting the GUI, which leaves room for batch rendering and future creative-coding front ends.

## Development

Run the test suite with:

```bash
python -m pytest
```

The tests cover color parsing, normalization bounds, deterministic generation, SVG output, aspect-aware geometry, and representative behavior profiles.

## Historical versions

`Versions/v_1`, `Versions/v_2`, and `Versions/v_3` remain as a development archive. The current application is the PySide6 implementation under `pattern_app/`.

## Roadmap

Future work can build on the current model with additional primitive families, non-linear composition fields, palette harmony modes, masks, layer blend modes, batch generation, seed browsing, animation-ready parameter interpolation, richer SVG primitives, a Windows installer, and additional platform-specific release bundles.
