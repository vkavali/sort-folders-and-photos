# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller build spec for Semantic File Aggregator.

Produces a windowed (no-console) desktop bundle at
    dist/SemanticFileAggregator/SemanticFileAggregator[.exe]

Usage:
    pyinstaller --noconfirm SemanticFileAggregator.spec

Cross-platform: works on Windows, macOS, and Linux. On macOS it additionally
assembles a .app bundle via the BUNDLE() stanza below.
"""

from PyInstaller.utils.hooks import collect_submodules

hiddenimports = collect_submodules("app")

a = Analysis(
    ["app/main.py"],
    pathex=[],
    binaries=[],
    datas=[],
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="SemanticFileAggregator",
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
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="SemanticFileAggregator",
)

app = BUNDLE(
    coll,
    name="SemanticFileAggregator.app",
    icon=None,
    bundle_identifier="com.semanticfileaggregator.app",
    info_plist={
        "CFBundleName": "Semantic File Aggregator",
        "CFBundleDisplayName": "Semantic File Aggregator",
        "CFBundleShortVersionString": "1.0.0",
        "NSHighResolutionCapable": True,
    },
)
