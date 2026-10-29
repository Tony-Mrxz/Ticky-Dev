# -*- mode: python ; coding: utf-8 -*-
import re
import sys
import os

is_win = sys.platform == 'win32'


def stamp_version_info():
    """Rewrite version_info.txt with utils/version.py so the exe metadata cannot lag the app.

    version_info.txt stays the template for the fixed strings (company, copyright);
    only the numbers are regenerated, into the build directory.
    """
    with open(os.path.join(SPECPATH, 'utils', 'version.py'), encoding='utf-8') as handle:
        app_version = re.search(r"APP_VERSION\s*=\s*['\"]([^'\"]+)['\"]", handle.read()).group(1)
    parts = tuple(int(n) for n in app_version.split('.'))[:3]
    quadruple = '(%d, %d, %d, 0)' % parts

    with open(os.path.join(SPECPATH, 'version_info.txt'), encoding='utf-8') as handle:
        text = handle.read()
    text = re.sub(r'filevers=\([\d, ]+\)', 'filevers=%s' % quadruple, text)
    text = re.sub(r'prodvers=\([\d, ]+\)', 'prodvers=%s' % quadruple, text)
    text = re.sub(r"(StringStruct\('FileVersion', )'[^']*'\)", r"\g<1>'%s')" % app_version, text)
    text = re.sub(r"(StringStruct\('ProductVersion', )'[^']*'\)", r"\g<1>'%s')" % app_version, text)

    target_dir = os.path.join(SPECPATH, 'build', 'Ticky')
    os.makedirs(target_dir, exist_ok=True)
    target = os.path.join(target_dir, 'version_info.generated.txt')
    with open(target, 'w', encoding='utf-8') as handle:
        handle.write(text)
    print('[Ticky.spec] stamping exe version info with %s' % app_version)
    return target


version_file = stamp_version_info() if is_win else None

# SMTC media control, text injection and the speech model are all late/dynamic
# imports, so PyInstaller cannot see them by itself.
winrt_hiddenimports = [
    'winrt',
    'winrt.windows.media.control',
    'winrt.windows.storage.streams',
    'winrt.windows.foundation',
    'winrt.windows.foundation.collections',
    'winrt.windows.media'
] if is_win else []

from PyInstaller.utils.hooks import collect_dynamic_libs, collect_data_files

# faster-whisper runs on ctranslate2, whose native DLLs (and OpenMP runtime) are
# loaded at import time from inside the package directory.
native_binaries = collect_dynamic_libs('ctranslate2') + collect_dynamic_libs('faster_whisper')
native_data = collect_data_files('ctranslate2')

# Assets are read relative to the bundle root at runtime (utils/icon.py,
# ui/onboarding_window.py), so they must land next to the entry point.
asset_datas = [
    ('styles/fonts', 'styles/fonts'),
    ('ticky-1.png', '.'),
    ('ticky.ico', '.'),
    ('ticky.png', '.'),
] + native_binaries + native_data

# build_installer.ps1 stages the offline speech model here; a plain
# `pyinstaller Ticky.spec` from a dev checkout simply skips it.
MODEL_DIR = os.path.join(SPECPATH, 'models', 'whisper')
if os.path.isdir(MODEL_DIR):
    asset_datas.append((MODEL_DIR, 'models/whisper'))
    print(f'[Ticky.spec] bundling offline speech model from {MODEL_DIR}')
else:
    print('[Ticky.spec] models/whisper missing - dictation will download on first use')

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=native_binaries,
    datas=asset_datas,
    hiddenimports=winrt_hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['vosk', 'torch', 'torchaudio', 'matplotlib', 'scipy'],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

if sys.platform == 'darwin':
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
    # One directory, not one file: no per-launch self-extraction to %TEMP%, which
    # keeps cold start under a second and avoids most antivirus false positives.
    exe = EXE(
        pyz,
        a.scripts,
        [],
        exclude_binaries=True,
        name='Ticky',
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
        version=version_file,
        icon=['ticky.ico'],
    )
    coll = COLLECT(
        exe,
        a.binaries,
        a.datas,
        strip=False,
        upx=False,
        upx_exclude=[],
        name='Ticky',
    )
