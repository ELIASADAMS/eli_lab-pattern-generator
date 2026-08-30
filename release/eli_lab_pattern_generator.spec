# PyInstaller one-file spec for the eli_lab Pattern Generator.
# Build from the repository root:
#   python -m PyInstaller --noconfirm --clean release/eli_lab_pattern_generator.spec

from pathlib import Path

from PyInstaller.building.build_main import Analysis, EXE, PYZ

ROOT = Path(SPEC).resolve().parent.parent
ICON = ROOT / "Icon" / "favicon.ico"
ENTRY = ROOT / "run.py"

if not ICON.exists():
    raise FileNotFoundError(f"Application icon not found: {ICON}")
if not ENTRY.exists():
    raise FileNotFoundError(f"Application entry point not found: {ENTRY}")


a = Analysis(
    [str(ENTRY)],
    pathex=[str(ROOT)],
    binaries=[],
    datas=[],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["PyQt5", "PyQt6", "PySide2"],
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=None)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    a.zipfiles,
    name="eli_lab-pattern-generator",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(ICON),
)
