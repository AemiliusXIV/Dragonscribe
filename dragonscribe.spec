# PyInstaller build spec for Dragonscribe.
# Built as a one-folder (--onedir) app: a Dragonscribe.exe alongside its files,
# zipped for release. onedir trips fewer antivirus heuristics than onefile.

block_cipher = None

a = Analysis(
    ['run.py'],
    pathex=[],
    binaries=[],
    datas=[('dragonscribe/ui/index.html', 'dragonscribe/ui')],
    hiddenimports=[
        'webview.platforms.edgechromium',
        'webview.platforms.winforms',
    ],
    hookspath=[],
    runtime_hooks=[],
    excludes=['tkinter', 'pytest'],
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='Dragonscribe',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,            # windowed app, no console flash
    disable_windowed_traceback=False,
    icon=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    name='Dragonscribe',
)
