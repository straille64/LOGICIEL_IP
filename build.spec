# build.spec
from PyInstaller.utils.hooks import collect_all

ttkb_datas, ttkb_binaries, ttkb_hiddenimports = collect_all('ttkbootstrap')
mac_datas, mac_binaries, mac_hiddenimports = collect_all('mac_vendor_lookup')
pymod_datas, pymod_binaries, pymod_hiddenimports = collect_all('pymodbus')
serial_datas, serial_binaries, serial_hiddenimports = collect_all('serial')
bac0_datas, bac0_binaries, bac0_hiddenimports = collect_all('BAC0')
bacpypes3_datas, bacpypes3_binaries, bacpypes3_hiddenimports = collect_all('bacpypes3')

block_cipher = None

a = Analysis(
    ['main.py'],
    pathex=['.'],
    binaries=ttkb_binaries + mac_binaries + pymod_binaries + serial_binaries + bac0_binaries + bacpypes3_binaries,
    datas=[('profiles', 'profiles'), ('assets', 'assets'), ('icones', 'icones')] + ttkb_datas + mac_datas + pymod_datas + serial_datas + bac0_datas + bacpypes3_datas,
    hiddenimports=['psutil', 'aiosqlite', 'dotenv', 'pytz'] + ttkb_hiddenimports + mac_hiddenimports + pymod_hiddenimports + serial_hiddenimports + bac0_hiddenimports + bacpypes3_hiddenimports,
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
    name='MultiTools_Z',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    manifest='app.manifest',
    icon='assets/icon.ico' if __import__('os').path.exists('assets/icon.ico') else None,
)
