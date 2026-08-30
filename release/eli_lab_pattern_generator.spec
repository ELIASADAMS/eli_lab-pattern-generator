# PyInstaller spec for the eli_lab Pattern Generator.
# Run from the repository root:
#   python -m PyInstaller --noconfirm --clean release/eli_lab_pattern_generator.spec

from pathlib import Path

from PyInstaller.building.build_main import Analysis, COLLECT, EXE, PYZ


ROOT = Path(SPEC).resolve().parent.parent
ICON = ROOT / "Icon" / "favicon.ico"

if not ICON.exists():
    raise FileNotFoundError(f"Application icon not found: {ICON}")


a = Analysis(
    [str(ROOT / "pattern_app" / "main.py")],
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
    [],
    exclude_binaries=True,
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

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    a.zipfiles,
    a.scripts,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="eli_lab-pattern-generator",
)
