import zipfile
import os
import datetime
import shutil


def create_release_zip():
    # Get script directory and set paths relative to project root
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_dir = os.path.dirname(script_dir)

    # Get version from pyproject.toml
    version = "unknown"
    try:
        pyproject_path = os.path.join(project_dir, "pyproject.toml")
        if os.path.exists(pyproject_path):
            with open(pyproject_path, "r", encoding="utf-8") as f:
                for line in f:
                    if line.strip().startswith("version = "):
                        version = line.split("=")[1].strip().strip('"').strip("'")
                        break
    except Exception as e:
        print(f"Warning: Could not read version: {e}")

    # Generate ZIP filename
    now = datetime.datetime.now()
    datestamp = now.strftime("%Y%m%d_%H%M%S")
    zip_filename = f"semantic_tester_windows_v{version}_{datestamp}.zip"

    release_dir = os.path.join(project_dir, "release_windows")
    zip_path = os.path.join(project_dir, zip_filename)

    print(f"Script dir: {script_dir}")
    print(f"Project dir: {project_dir}")
    print(f"Release dir: {release_dir}")
    print(f"Zip path: {zip_path}")

    # Always create release directory and copy files
    print("Creating release directory and copying files...")
    os.makedirs(release_dir, exist_ok=True)

    # 1. Copy executable
    # 优先从 release_windows 目录获取（与 build_windows.bat 的 --distpath 保持一致）
    exe_source_primary = os.path.join(release_dir, "semantic_tester.exe")
    dist_dir = os.path.join(project_dir, "dist")
    exe_source_fallback = os.path.join(dist_dir, "semantic_tester.exe")
    exe_path = os.path.join(release_dir, "semantic_tester.exe")

    if os.path.exists(exe_source_primary):
        # 已经在 release_windows 中，无需再次复制，只做存在性校验
        print("  Found semantic_tester.exe in release_windows")
    elif os.path.exists(exe_source_fallback):
        # 兼容旧流程：从 dist 复制到 release_windows
        shutil.copy2(exe_source_fallback, exe_path)
        print("  Copied semantic_tester.exe from dist to release_windows")
    else:
        print(
            f"  Warning: Executable not found in release_windows or dist (checked: {exe_source_primary}, {exe_source_fallback})"
        )

    # 2. Copy config template
    config_src = os.path.join(project_dir, ".env.config.example")
    config_dst = os.path.join(release_dir, ".env.config.example")
    if os.path.exists(config_src):
        shutil.copy2(config_src, config_dst)
        print("  Copied .env.config.example")

    # 3. Copy README
    readme_src = os.path.join(project_dir, "README.md")
    readme_dst = os.path.join(release_dir, "README.md")
    if os.path.exists(readme_src):
        shutil.copy2(readme_src, readme_dst)
        print("  Copied README.md")

    # 4. Create usage instructions
    usage_content = """# 🤖 Semantic Tester Usage Guide

## 1. Preparation
- Ensure you have the `semantic_tester.exe` executable.
- Ensure you have the `.env.config.example` configuration template.
- Prepare your knowledge base documents (Markdown format) in the `kb-docs` folder.

## 2. Configuration
1. Copy `.env.config.example` to `.env.config`.
2. Open `.env.config` with a text editor (e.g., Notepad).
3. Fill in your API keys (Gemini, OpenAI, Dify, etc.).

## 3. Running
1. Double-click `semantic_tester.exe` to start the program.
2. Follow the on-screen instructions to select your Excel file and knowledge base directory.

## 4. Viewing Results
- The program will process the Excel file and write the results back to it.
- Logs are saved in the `logs` directory.
"""
    with open(os.path.join(release_dir, "usage_guide.md"), "w", encoding="utf-8") as f:
        f.write(usage_content)
    print("  Created usage_guide.md")

    # 5. Compress
    print(f"Creating ZIP archive: {zip_filename}")
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(release_dir):
            for file in files:
                file_path = os.path.join(root, file)
                arcname = os.path.relpath(file_path, release_dir)
                zipf.write(file_path, arcname)
                print(f"  Added: {arcname}")

    # Check file size
    if os.path.exists(zip_path):
        size_mb = os.path.getsize(zip_path) / (1024 * 1024)
        print(f"\n✅ ZIP archive created successfully: {zip_path}")
        print(f"   Size: {size_mb:.2f} MB")
    else:
        print("\n❌ Failed to create ZIP archive")


if __name__ == "__main__":
    create_release_zip()
