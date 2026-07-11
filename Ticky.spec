# -*- mode: python ; coding: utf-8 -*-
import sys
import os

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[('styles/fonts', 'styles/fonts')],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

is_mac = sys.platform == 'darwin'

exe_icon = 'ticky.icns' if is_mac else 'ticky.ico'
if is_mac and not os.path.exists(exe_icon):
    exe_icon = None

exe = EXE(
    pyz,
    a.scripts,
    # If on Mac, we build as a directory/bundle structure, so we don't pack binaries in EXE
    a.binaries if not is_mac else [],
    a.zipfiles if not is_mac else [],
    a.datas if not is_mac else [],
    [],
    name='Ticky',
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
    version=None if is_mac else 'version_info.txt',
    icon=exe_icon,
)

if is_mac:
    coll = COLLECT(
        exe,
        a.binaries,
        a.zipfiles,
        a.datas,
        strip=False,
        upx=True,
        upx_exclude=[],
        name='Ticky'
    )
    app = BUNDLE(
        coll,
        name='Ticky.app',
        icon='ticky.icns' if os.path.exists('ticky.icns') else None,
        bundle_identifier='com.ticky.dev',
    )
