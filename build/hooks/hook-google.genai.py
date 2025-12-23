# PyInstaller hook for google-genai (handles namespace package correctly)
from PyInstaller.utils.hooks import (
    collect_all,
    collect_submodules,
    collect_data_files,
    get_all_package_paths,
    is_package,
)

# google.genai 是 google 命名空间包的一部分，需要特殊处理
datas = []
binaries = []
hiddenimports = []

# 收集 google.genai 的所有内容
if is_package('google.genai'):
    _datas, _binaries, _hiddenimports = collect_all('google.genai')
    datas += _datas
    binaries += _binaries
    hiddenimports += _hiddenimports

# 对于命名空间包，需要收集所有路径
try:
    pkg_paths = get_all_package_paths('google')
    for path in pkg_paths:
        datas += collect_data_files('google', path)
except Exception:
    pass

# 确保 google 命名空间包本身被正确处理
hiddenimports += collect_submodules('google.genai')
hiddenimports += collect_submodules('google.auth')
hiddenimports += collect_submodules('google.api_core')

# 显式添加关键模块
hiddenimports += [
    'google',
    'google.genai',
    'google.genai.types',
    'google.genai._api_client',
    'google.genai.client',
    'google.genai.models',
    'google.auth',
    'google.auth.transport',
    'google.auth.transport.requests',
    'google.api_core',
    'google.api_core.exceptions',
    'google.api_core.gapic_v1',
    'httpx',
    'httpcore',
    'anyio',
    'sniffio',
    'h11',
    'tenacity',
    'websockets',
]
