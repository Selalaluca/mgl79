# -*- mode: python ; coding: utf-8 -*-

import sys
from pathlib import Path


PROJECT_ROOT = Path(SPECPATH).resolve()
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from mgl77.config import EXECUTABLE_NAME


a = Analysis(
    [str(PROJECT_ROOT / "src" / "mgl77" / "main.py")],
    pathex=[str(PROJECT_ROOT / "src")],
    binaries=[],
    datas=[],
    hiddenimports=["win32gui", "win32con", "win32api", "pyautogui"],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name=EXECUTABLE_NAME,
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
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
    strip=False,
    upx=True,
    upx_exclude=[],
    name=EXECUTABLE_NAME,
)
