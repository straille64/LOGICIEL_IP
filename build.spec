# build.spec
from PyInstaller.utils.hooks import collect_all

ttkb_datas, ttkb_binaries, ttkb_hiddenimports = collect_all('ttkbootstrap')
mac_datas, mac_binaries, mac_hiddenimports = collect_all('mac_vendor_lookup')

block_cipher = None

a = Analysis(
    ['main.py'],
    pathex=['.'],
    binaries=ttkb_binaries + mac_binaries,
    datas=[('profiles', 'profiles'), ('assets', 'assets')] + ttkb_datas + mac_datas,
    hiddenimports=['psutil'] + ttkb_hiddenimports + mac_hiddenimports,
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
