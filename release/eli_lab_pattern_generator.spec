# PyInstaller spec for the eli_lab Pattern Generator.
# Build from the repository root with:
#   python -m PyInstaller --noconfirm --clean release/eli_lab_pattern_generator.spec

from PyInstaller.building.build_main import Analysis, PYZ, EXE, COLLECT

block_cipher = None


a = Analysis(
    ['pattern_app/main.py'],
    pathex=['.'],
    binaries=[],
    datas=[],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['PyQt5', 'PyQt6', 'PySide2'],
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='eli_lab-pattern-generator',
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
    name='eli_lab-pattern-generator',
)
