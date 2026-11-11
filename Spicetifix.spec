# -*- mode: python ; coding: utf-8 -*-
import os

from PyInstaller.utils.hooks import collect_all

# ``SPECPATH`` is injected by PyInstaller and points at the directory holding
# this spec, so the build no longer hardcodes the author's absolute paths.
PROJECT_ROOT = os.path.abspath(SPECPATH)

datas = [(os.path.join(PROJECT_ROOT, 'web'), 'web')]
binaries = []
hiddenimports = ['tkinter', 'tkinter.filedialog', 'pythonnet', 'clr_loader']
tmp_ret = collect_all('spicetifix')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]
tmp_ret = collect_all('webview')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]


a = Analysis(
    [os.path.join(PROJECT_ROOT, 'main.py')],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['PyQt5', 'PyQt6', 'Pyside6'],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='Spicetifix',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
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
    strip=False,
    upx=False,
    upx_exclude=[],
    name='Spicetifix',
)
