# -*- mode: python ; coding: utf-8 -*-
from pathlib import Path
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

ROOT = Path(SPECPATH).resolve().parent

a = Analysis(
    [str(ROOT / 'gui_app.py')],
    pathex=[str(ROOT)],
    binaries=[],
    datas=[(str(ROOT / '.release-build' / 'build-info.json'), 'ytb_bot'),
           (str(ROOT / 'frontend' / 'web-dist'), 'frontend/web-dist')] + collect_data_files('webview') + collect_data_files('tzdata'),
    hiddenimports=['openpyxl', 'xlrd', 'webview.platforms.winforms', 'webview.platforms.edgechromium'] + collect_submodules('tzdata'),
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['PyQt5', 'PyQt6', 'PySide2', 'PySide6', 'webview.platforms.qt', 'webview.platforms.gtk'],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='gui_app',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
