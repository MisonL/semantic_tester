@echo off
setlocal enabledelayedexpansion

echo ==========================================
echo Semantic Tester Windows 打包脚本
echo ==========================================

REM Get script directory
set SCRIPT_DIR=%~dp0
REM Get project root directory
set PROJECT_DIR=%SCRIPT_DIR%..

REM Switch to project root directory
cd /d "%PROJECT_DIR%"

echo 项目目录: %PROJECT_DIR%
echo 构建目录: %SCRIPT_DIR%
echo ==========================================

REM Check if py launcher is available
where py >nul 2>nul
if %errorlevel% neq 0 (
    echo 错误: 未找到 Python py 启动器
    echo 请先安装 Python
    pause
    exit /b 1
)

REM Check if uv is installed
py -m uv --version >nul 2>nul
if %errorlevel% neq 0 (
    echo 错误: uv 未安装
    echo 正在安装 uv...
    py -m pip install uv
)

REM Check Python version
echo 检查 Python 版本...
py -m uv run python --version

REM Install/update dependencies
echo 安装/更新依赖...
py -m uv sync

REM Install PyInstaller
echo 安装 PyInstaller...
py -m uv add --dev pyinstaller

REM Clean previous build
echo 清理之前的构建...
if exist "%PROJECT_DIR%\dist\" (
    rmdir /s /q "%PROJECT_DIR%\dist\" 2>nul
)
if exist "%PROJECT_DIR%\release_windows\" (
    rmdir /s /q "%PROJECT_DIR%\release_windows\" 2>nul
)
if exist "%PROJECT_DIR%\build\semantic_tester\" (
    rmdir /s /q "%PROJECT_DIR%\build\semantic_tester\" 2>nul
)
if exist "%PROJECT_DIR%\build\semantic_tester.dist\" (
    rmdir /s /q "%PROJECT_DIR%\build\semantic_tester.dist\" 2>nul
)
if exist "%PROJECT_DIR%\build\semantic_tester.build\" (
    rmdir /s /q "%PROJECT_DIR%\build\semantic_tester.build\" 2>nul
)

REM Use spec file from build directory
set SPEC_FILE=%SCRIPT_DIR%semantic_tester.spec
if not exist "%SPEC_FILE%" (
    echo 错误: 在 %SPEC_FILE% 未找到 spec 文件
    pause
    exit /b 1
)

echo 使用 spec 文件: %SPEC_FILE%

REM Run PyInstaller
echo 开始打包...
py -m uv run pyinstaller --distpath "%PROJECT_DIR%\release_windows" "%SPEC_FILE%"

REM Check build result
if not exist "%PROJECT_DIR%\release_windows\semantic_tester.exe" goto :FAILURE

:SUCCESS
echo.
echo 构建成功！
echo 可执行文件位置: %PROJECT_DIR%\release_windows\semantic_tester.exe

REM Create compressed package
echo 创建压缩包...

cd /d "%PROJECT_DIR%"

REM Create ZIP archive (Python script handles file copying and zipping)
echo 创建 ZIP 压缩包...
py "%SCRIPT_DIR%create_release_zip.py"

echo.
echo 使用说明:
echo 1. 解压 semantic_tester_windows_v*.zip
echo 2. 复制 .env.config.example 为 .env.config
echo 3. 编辑 .env.config 配置 API 信息
echo 4. 准备知识库文档 (放在 kb-docs 目录)
echo 5. 双击 semantic_tester.exe 启动程序
echo.
echo 打包完成！

REM Clean up temporary build directories
echo 清理临时文件...
if exist "%PROJECT_DIR%\build\semantic_tester\" (
    rmdir /s /q "%PROJECT_DIR%\build\semantic_tester\" 2>nul
)
if exist "%PROJECT_DIR%\build\semantic_tester.dist\" (
    rmdir /s /q "%PROJECT_DIR%\build\semantic_tester.dist\" 2>nul
)
if exist "%PROJECT_DIR%\build\semantic_tester.build\" (
    rmdir /s /q "%PROJECT_DIR%\build\semantic_tester.build\" 2>nul
)
echo 清理完成。

goto :END

:FAILURE
echo.
echo 构建失败！
echo 请检查错误信息并重试
pause
exit /b 1

:END
pause
