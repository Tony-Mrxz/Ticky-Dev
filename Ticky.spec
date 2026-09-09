# -*- mode: python ; coding: utf-8 -*-
import sys
import os

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[('styles/fonts', 'styles/fonts')],
    hiddenimports=[
        'winrt',
        'winrt.windows.media.control',
        'winrt.windows.storage.streams',
        'winrt.windows.foundation',
        'winrt.windows.foundation.collections',
        'winrt.windows.media'
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

is_mac = sys.platform == 'darwin'

if is_mac:
    # On macOS, build in "onedir" mode (exclude binaries from EXE) and collect them in a BUNDLE
    exe = EXE(
        pyz,
        a.scripts,
        exclude_binaries=True,
        name='Ticky',
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
        icon=None,
    )
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
        icon=None,
        bundle_identifier='com.ticky.dev',
    )
else:
    # On Windows, build in "onefile" mode (pack everything into the EXE)
    exe = EXE(
        pyz,
        a.scripts,
        a.binaries,
        a.datas,
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
        version='version_info.txt',
        icon=['ticky.ico'],
    )
