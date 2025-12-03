@echo off
setlocal enabledelayedexpansion

echo ==========================================
echo Semantic Tester Windows Build Script (v3.0.1 Fixed)
echo ==========================================

REM Get script directory
set SCRIPT_DIR=%~dp0
REM Get project root directory
set PROJECT_DIR=%SCRIPT_DIR%..

REM Switch to project root directory
cd /d "%PROJECT_DIR%"

echo Project directory: %PROJECT_DIR%
echo Build directory: %SCRIPT_DIR%
echo ==========================================

REM Check if py launcher is available
where py >nul 2>nul
if %errorlevel% neq 0 (
    echo Error: Python py launcher not found
    echo Please install Python first
    pause
    exit /b 1
)

REM Check if uv is installed
py -m uv --version >nul 2>nul
if %errorlevel% neq 0 (
    echo Error: uv not installed
    echo Installing uv...
    py -m pip install uv
)

REM Check Python version
echo Checking Python version...
py -m uv run python --version

REM Install/update dependencies
echo Installing/updating dependencies...
py -m uv sync

REM Install PyInstaller
echo Installing PyInstaller...
py -m uv add --dev pyinstaller

REM Clean previous build
echo Cleaning previous build...
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
    echo Error: Spec file not found at %SPEC_FILE%
    pause
    exit /b 1
)

echo Using spec file: %SPEC_FILE%

REM Run PyInstaller
echo Starting packaging...
py -m uv run pyinstaller --distpath "%PROJECT_DIR%\release_windows" "%SPEC_FILE%"

REM Check build result
if not exist "%PROJECT_DIR%\release_windows\semantic_tester.exe" goto :FAILURE

:SUCCESS
echo.
echo Build successful!
echo Executable location: %PROJECT_DIR%\release_windows\semantic_tester.exe

REM Create compressed package
echo Creating compressed package...

cd /d "%PROJECT_DIR%"

REM Create ZIP archive (Python script handles file copying and zipping)
echo Creating ZIP archive...
py "%SCRIPT_DIR%create_release_zip.py"

echo.
echo Usage instructions:
echo 1. Extract semantic_tester_windows_v*.zip
echo 2. Copy .env.config.example to .env.config
echo 3. Edit .env.config to configure API information
echo 4. Prepare knowledge base documents (in kb-docs directory)
echo 5. Double-click semantic_tester.exe to start the program
echo.
echo Packaging complete!
goto :END

:FAILURE
echo.
echo Build failed!
echo Please check error messages and retry
pause
exit /b 1

:END
pause
