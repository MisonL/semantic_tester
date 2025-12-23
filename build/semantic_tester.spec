# -*- mode: python ; coding: utf-8 -*-
"""
AI客服问答语义比对工具 - PyInstaller 打包配置文件 (Simplified)
"""

import os
import sys
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

# 获取项目根目录
spec_dir = os.path.dirname(os.path.abspath(sys.argv[0]))
if os.path.basename(spec_dir) == 'build':
    project_root = os.path.abspath(os.path.join(spec_dir, '..'))
else:
    project_root = spec_dir

# 主程序文件
main_script = os.path.join(project_root, 'main.py')

# 收集数据文件
datas = [
    (os.path.join(project_root, '.env.config.example'), '.'),
    (os.path.join(project_root, 'README.md'), '.',) if os.path.exists(os.path.join(project_root, 'README.md')) else None,
]
datas = [d for d in datas if d is not None]

# 仅收集关键依赖，其他的让 PyInstaller 自动分析
hiddenimports = []

# 收集 google.genai 依赖 (使用我们自定义的 hook 还不够，显式添加更保险)
# 但不再添加庞大的无关列表
hiddenimports += collect_submodules('google.genai')
hiddenimports += collect_submodules('pydantic')

# 收集数据文件
datas += collect_data_files('google.genai')
datas += collect_data_files('pydantic')

binaries = []

# 排除不需要的模块 (参考 dify_chat_tester)
excludes = [
    'matplotlib',
    'scipy',
    'tkinter',
    'PyQt5',
    'PyQt6',
    'PySide2',
    'PySide6',
    'IPython',
    'jupyter',
    'notebook',
    'PIL',
    'cv2',
]

a = Analysis(
    [main_script],
    pathex=[project_root],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    # 仍然使用我们的 hooks 目录，因为 hook-google.genai.py 很有用
    hookspath=[os.path.join(spec_dir, 'hooks')], 
    hooksconfig={},
    # 保留 SSL 修复 hook，因为那是针对具体报错的修复
    runtime_hooks=[os.path.join(spec_dir, 'rthooks', 'pyi_rth_ssl_fix.py')],
    excludes=excludes,
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=None,
    noarchive=False,
)

# 移除 Windows 系统 DLL (参考 dify_chat_tester)
for exclude in ['api-ms-win-*.dll', 'ucrtbase.dll', 'msvcp*.dll', 'vcruntime*.dll']:
    a.binaries = [x for x in a.binaries if not x[0].startswith(exclude)]

pyz = PYZ(a.pure, a.zipped_data, cipher=None)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='semantic_tester',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    # icon=os.path.join(project_root, 'assets', 'icon.ico'), # 如果有图标
)
