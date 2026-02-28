# build.spec
block_cipher = None

a = Analysis(
    ['main.py'],
    pathex=['.'],
    binaries=[],
    datas=[('profiles', 'profiles'), ('assets', 'assets')],
    hiddenimports=['ttkbootstrap', 'psutil'],
    hookspath=[],
    runtime_hooks=[],
    excludes=[],
    cipher=block_cipher,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    name='LOGICIEL_IP',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    manifest='app.manifest',
    icon='assets/icon.ico' if __import__('os').path.exists('assets/icon.ico') else None,
)
