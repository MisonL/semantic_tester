# -*- coding: utf-8 -*-
"""
运行时 Hook：修复 Windows SSL DLL 加载问题

PyInstaller 的 bootloader 会修改 Windows 的 DLL 搜索目录，
这可能导致 Python 的 _ssl 模块在加载 OpenSSL DLL 时失败。
此 hook 在程序启动时重置 DLL 搜索路径，确保 SSL 正常工作。

必须在其他所有模块导入之前执行！
"""
import sys
import os

if sys.platform == "win32":
    try:
        import ctypes
        from ctypes import wintypes
        
        # 获取 kernel32 句柄
        kernel32 = ctypes.windll.kernel32
        
        # 方法1：重置 DLL 搜索路径到默认值
        # 这会撤销 PyInstaller bootloader 对 SetDllDirectory 的修改
        try:
            kernel32.SetDllDirectoryW(None)
        except Exception:
            pass
        
        # 方法2：将 _MEIPASS 添加到 DLL 搜索路径
        if hasattr(sys, '_MEIPASS'):
            meipass = sys._MEIPASS
            
            # 确保 _MEIPASS 在 PATH 环境变量最前面
            current_path = os.environ.get('PATH', '')
            if meipass not in current_path:
                os.environ['PATH'] = meipass + os.pathsep + current_path
            
            # 使用 AddDllDirectory 添加 DLL 搜索路径（Windows 8+）
            try:
                add_dll_directory = kernel32.AddDllDirectory
                add_dll_directory.argtypes = [wintypes.LPCWSTR]
                add_dll_directory.restype = wintypes.HANDLE
                add_dll_directory(meipass)
            except Exception:
                pass
            
            # 使用 SetDefaultDllDirectories 设置默认搜索顺序
            try:
                # LOAD_LIBRARY_SEARCH_DEFAULT_DIRS = 0x00001000
                # LOAD_LIBRARY_SEARCH_USER_DIRS = 0x00000400
                # LOAD_LIBRARY_SEARCH_APPLICATION_DIR = 0x00000200
                kernel32.SetDefaultDllDirectories(0x00001000 | 0x00000400 | 0x00000200)
            except Exception:
                pass
                
    except Exception:
        # 如果出错，静默忽略，让程序继续启动
        pass
