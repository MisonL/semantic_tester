# -*- mode: python ; coding: utf-8 -*-
"""
AI客服问答语义比对工具 - PyInstaller 打包配置文件
"""

import os
import sys
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

# 获取项目根目录
# 使用 sys.argv[0] 获取spec文件路径，避免 __file__ 未定义错误
spec_dir = os.path.dirname(os.path.abspath(sys.argv[0]))
# 检查spec文件是否在项目根目录下
if os.path.basename(spec_dir) == 'build':
    # spec文件在build目录下
    project_root = os.path.abspath(os.path.join(spec_dir, '..'))
else:
    # spec文件在项目根目录下
    project_root = spec_dir

# 主程序文件
main_script = os.path.join(project_root, 'main.py')

# 获取发布目录
release_dir = os.path.join(project_root, 'release_windows')

# 收集数据文件
datas = [
    # 配置文件模板
    (os.path.join(project_root, '.env.config.example'), '.'),
    
    # README文件（如果存在）
    (os.path.join(project_root, 'README.md'), '.',) if os.path.exists(os.path.join(project_root, 'README.md')) else None,
]

# 过滤掉 None 值
datas = [d for d in datas if d is not None]

# 收集隐藏导入
hiddenimports = [
    'semantic_tester.api',
    'semantic_tester.api.base_provider',
    'semantic_tester.api.gemini_provider',
    'semantic_tester.api.openai_provider',
    'semantic_tester.api.dify_provider',
    'semantic_tester.api.anthropic_provider',
    'semantic_tester.api.iflow_provider',
    'semantic_tester.api.provider_manager',
    'semantic_tester.api.prompts',
    'semantic_tester.config',
    'semantic_tester.config.settings',
    'semantic_tester.config.environment',
    'semantic_tester.config.env_loader',
    'semantic_tester.excel',
    'semantic_tester.excel.processor',
    'semantic_tester.ui',
    'semantic_tester.ui.cli',
'semantic_tester.utils',
    # 以下模块已不再使用或由依赖自动处理，无需强制作为 hiddenimports
    # 'semantic_tester.utils.file_handler',
    # 'semantic_tester.utils.logger',
    # 'google.generativeai',
    # 'google.ai.generativelanguage',
    # 'google.api_core',
    'openai',
    'requests',
    'requests.adapters',
    'requests.auth',
    'requests.exceptions',
    'requests.models',
    'requests.sessions',
    'requests.utils',
    'openpyxl',
    'openpyxl.workbook',
    'openpyxl.worksheet',
    'openpyxl.cell',
    'openpyxl.styles',
    'openpyxl.utils',
    'pandas',
    'colorama',
    'colorama.ansi',
    'colorama.initialise',
    'colorama.win32',
    'dotenv',
    'ctypes',
    'ctypes.wintypes',
    'datetime',
    'json',
    'os',
    'sys',
    'time',
    're',
    'urllib.parse',
    'threading',
    'uuid',
    'pathlib',
]

# 收集二进制文件
binaries = []

# 排除不需要的模块
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
]

a = Analysis(
    [main_script],
    pathex=[project_root],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=excludes,
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=None,
    noarchive=False,
)

# 移除不需要的二进制文件（Windows特定）
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
    icon=None,
)
