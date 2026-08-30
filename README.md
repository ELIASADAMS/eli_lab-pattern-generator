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

## Parameter model

The controls are organized by the role they play in the generative system.

### Composition

**Composition mode** determines where material wants to exist: balanced, focal, clustered, edge-biased, or diagonal.

**Focal X/Y** and **focal strength** establish a compositional attractor. **Cluster count** and **cluster strength** create local concentration fields. **Spacing** controls how tightly geometry fills its cell. **Position jitter** adds displacement without changing the underlying grid.

### Field

The vector field is shared by flow lines and geometric drift. **Field mode** selects the directional system: noise, swirl, vortex, waves, radial, or none.

**Field strength** controls displacement. **Scale** controls spatial frequency. **Curvature** controls how strongly a path follows its local field direction. **Steps** and **step size** control trajectory length and resolution. **Octaves** add multi-scale noise detail.

### Geometry

**Grid** defines structural resolution. **Shape scale** controls primitive size, while **scale variance** prevents a tiled, mechanical look. **Rotation** sets the global angle and **rotation jitter** introduces local orientation change.

**Corner roundness**, **line complexity**, and **overlap** control the visual vocabulary without changing the overall composition.

Primitive weights are probabilities rather than simple on/off switches. For example, a line weight of `3` and circle weight of `1` makes lines substantially more common without forcing every cell to be a line.

Geometry is normalized to a uniform spatial scale, so a circle remains a circle when the canvas changes from 16:9 to 9:16 or 1:1.

### Color

**Palette size** controls the active color vocabulary. **Saturation** and **contrast** reshape that palette. **Hue jitter** introduces controlled variation.

**Opacity min/max** define transparency range. **Color coherence** controls whether neighboring positions tend to reuse related palette regions or jump around the palette.

### Layers

Multiple layers reuse the same generator language through independent deterministic random streams. This creates additional spatial scales while preserving reproducibility.

**Depth** affects stroke/accent scale and visual weight. **Accent density** adds secondary particles. **Gradient background** and **raster blur** are finishing operations; SVG remains geometry-based.

### Behavior

Behavior presets are **parameter bundles**, not alternate algorithms:

- **Calm** reduces movement, variance, and mutation.
- **Organic** keeps balanced defaults.
- **Architectural** suppresses most field-driven movement and favors regular geometry.
- **Chaotic** increases curvature, scale variance, jitter, and mutation.
- **Ritual** emphasizes curved flow and concentrated/repeating structure.

The intention is to start from a behavioral family and then push individual parameters.

## Requirements

Python **3.10+** and a desktop environment supported by Qt 6.

Runtime dependencies are listed in `pyproject.toml` and `requirements.txt`:

- `PySide6>=6.10`
- `Pillow>=11.0`
- `opensimplex>=0.4`

Release/build dependencies are listed in `requirements-dev.txt` and include `build`, `pytest`, and PyInstaller.

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

PyCharm can use the repository's shared `eli_lab Pattern Generator` run configuration. The working directory is the repository root and the launcher is `run.py`.

Other supported forms:

```bash
python -m pattern_app.main
```

```bash
eli-pattern-generator
```

## Build a Windows release

The project has a reproducible **Windows x64 portable release** build based on PyInstaller. PyInstaller bundles the Python interpreter and application dependencies so end users do not need Python installed. Qt documents PyInstaller as a supported PySide6 deployment route.

Install the release toolchain:

```powershell
python -m pip install -r requirements-dev.txt
```

Run the complete local release build:

```powershell
powershell -ExecutionPolicy Bypass -File .\\scripts\\build-release.ps1
```

The script:

1. creates `.venv` when needed;
2. installs runtime and build dependencies;
3. runs the test suite;
4. builds the Python source distribution and wheel;
5. builds the PySide6 application with the tracked PyInstaller spec;
6. creates `release/artifacts/eli_lab-pattern-generator-windows-x64.zip`.

The portable Windows archive contains the executable and all required runtime files. Distribute the ZIP as-is; do not distribute the internal `build/` directory.

### Release naming

The package version lives in `pyproject.toml`.

Create a release tag using the same semantic version:

```powershell
git tag v2.1.0
git push origin v2.1.0
```

Pushing a `vMAJOR.MINOR.PATCH` tag starts `.github/workflows/release.yml`. CI verifies the tag matches `pyproject.toml`, runs tests, builds the Python distributions and Windows portable ZIP, and publishes all artifacts to the GitHub Release.

A manual workflow run is also available from GitHub Actions. Manual runs build and upload artifacts but intentionally do not publish a GitHub Release.

## Python package artifacts

Build the package locally without the Windows bundle:

```bash
python -m pip install -r requirements-dev.txt
python -m build
```

This creates `dist/*.tar.gz` and `dist/*.whl`.

Install the built wheel locally with:

```bash
python -m pip install dist/eli_lab_pattern_generator-*.whl
```

## Presets

Presets are ordinary JSON files containing the full `PatternConfig`. They are intended to be portable, diffable, and version-controllable.

## Architecture

```text
pattern_app/
├── __init__.py
├── generator.py        # Procedural renderer + SVG generator
├── main.py             # Stable application entry point
└── ui.py               # PySide6 editor UI

run.py                  # PyCharm/repository launcher
requirements.txt        # Runtime dependencies
requirements-dev.txt    # Development + release toolchain
pyproject.toml          # Packaging and console entry point
release/
└── eli_lab_pattern_generator.spec
scripts/
└── build-release.ps1
.github/
└── workflows/
    └── release.yml
.idea/
└── runConfigurations/  # Shared PyCharm run configuration

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
