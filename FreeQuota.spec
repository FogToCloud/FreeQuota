# -*- mode: python ; coding: utf-8 -*-
"""FreeQuota 的 PyInstaller 打包配置（生成 Windows 一键 exe）。

用法：
    pip install pyinstaller
    pyinstaller FreeQuota.spec
产物：dist/FreeQuota/FreeQuota.exe（双击即用）

要点：
- Streamlit 的前端静态目录必须随包收集，否则页面白屏。
- app.py / config.example.json 作为数据文件打进包，运行时由 launcher 取用。
- core 包通过 hiddenimports 显式收集（因为它由 app.py 在运行时动态 import）。
"""

import os
import glob
import streamlit
from PyInstaller.utils.hooks import collect_submodules

block_cipher = None

# 递归收集 streamlit 全部子模块。
# 必须这么做：streamlit 有不少内部模块（例如 streamlit.runtime.scriptrunner.magic_funcs）
# 是运行时按字符串动态导入的，静态分析扫不到。漏了它们会出现「页面能打开、app.py 也开始执行，
# 但随即报 ModuleNotFoundError」的怪现象，所以这里一次性全收。
_streamlit_submodules = collect_submodules("streamlit")

# 运行时钩子：在 App 导入前兜底 importlib.metadata（冻结态缺失 .dist-info 的崩溃修复）
# 注意：spec 执行时 __file__ 不可用，故用 cwd（打包始终在仓库目录下进行）定位钩子。
_RTH = os.path.join(os.getcwd(), "rth_metadata.py")

# 定位 Streamlit 前端静态资源目录（不同版本路径略有差异，兼容两种）
_streamlit_root = os.path.dirname(streamlit.__file__)
_static_candidates = [
    os.path.join(_streamlit_root, "static"),
    os.path.join(_streamlit_root, "web", "static"),
]
streamlit_static = None
for _c in _static_candidates:
    if os.path.isdir(_c):
        streamlit_static = os.path.abspath(_c)
        break
assert streamlit_static is not None, "找不到 Streamlit 的 static 目录，请检查 streamlit 安装"

# Streamlit（以及 pandas 等）在导入时会用 importlib.metadata 读取自身版本，
# 而 PyInstaller 默认不打 .dist-info 元数据，会导致 PackageNotFoundError 直接崩。
# 把所有 *.dist-info 一并打进包（放在 _MEIPASS 根目录，importlib.metadata 可在 sys.path 上找到）。
_site_packages = os.path.dirname(os.path.dirname(streamlit.__file__))
_extra_datas = []
for _d in glob.glob(os.path.join(_site_packages, "*.dist-info")):
    _extra_datas.append((_d, os.path.basename(_d)))

a = Analysis(
    ["launcher.py"],
    pathex=["."],
    binaries=[],
    datas=[
        ("app.py", "."),
        ("config.example.json", "."),
        (streamlit_static, "streamlit/static"),
    ] + _extra_datas,
    hiddenimports=[
        "core",
        "core.relay",
    ]
    + _streamlit_submodules
    + [
        "pyarrow",
        "pandas",
        "numpy",
        "httpx",
        "watchdog",
        "validators",
        "tzlocal",
        "toml",
        "packaging",
        "pkg_resources",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[_RTH],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="FreeQuota",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # 面向普通用户：不弹黑色命令行窗口；排错日志走 FreeQuota.log
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
    name="FreeQuota",
)
