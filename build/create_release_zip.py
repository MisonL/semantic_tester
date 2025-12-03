import zipfile
import os
import datetime
import shutil

def create_release_zip():
    """创建发布包ZIP文件"""
    # 获取脚本所在目录
    script_dir = os.path.dirname(os.path.abspath(__file__))
    # 获取项目根目录（脚本目录的父目录）
    project_root = os.path.dirname(script_dir)
    
    # 获取版本号
    version = "unknown"
    try:
        pyproject_path = os.path.join(project_root, 'pyproject.toml')
        if os.path.exists(pyproject_path):
            with open(pyproject_path, 'r', encoding='utf-8') as f:
                for line in f:
                    if line.strip().startswith('version = '):
                        version = line.split('=')[1].strip().strip('"').strip("'")
                        break
    except Exception as e:
        print(f"警告: 无法读取版本号: {e}")

    # 生成ZIP文件名
    timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    zip_filename = f'semantic_tester_windows_v{version}_{timestamp}.zip'
    zip_path = os.path.join(project_root, zip_filename)
    
    release_dir = os.path.join(project_root, 'release_windows')
    
    print(f"Script dir: {script_dir}")
    print(f"Project root: {project_root}")
    print(f"Release dir: {release_dir}")
    print(f"Zip path: {zip_path}")
    
    # 确保发布目录存在
    os.makedirs(release_dir, exist_ok=True)
    
    print("正在准备发布文件...")
    
    # 1. 复制可执行文件 (从 release_windows 或 dist 复制，这里假设 pyinstaller 已经输出到 release_windows)
    # 如果 pyinstaller 输出到了 release_windows，那么 exe 已经在里面了，不需要复制
    # 但为了保险，我们检查一下
    exe_path = os.path.join(release_dir, 'semantic_tester.exe')
    if not os.path.exists(exe_path):
        # 尝试从 dist 找
        dist_exe = os.path.join(project_root, 'dist', 'semantic_tester.exe')
        if os.path.exists(dist_exe):
            shutil.copy2(dist_exe, exe_path)
            print("  已从 dist 复制 semantic_tester.exe")
        else:
            print("  警告: 未找到 semantic_tester.exe")
    else:
        print("  semantic_tester.exe 已存在")

    # 2. 复制配置文件
    config_src = os.path.join(project_root, '.env.config.example')
    config_dst = os.path.join(release_dir, '.env.config.example')
    if os.path.exists(config_src):
        shutil.copy2(config_src, config_dst)
        print("  已复制 .env.config.example")
    else:
        print(f"  警告: 未找到配置文件 {config_src}")

    # 3. 复制 README
    readme_src = os.path.join(project_root, 'README.md')
    readme_dst = os.path.join(release_dir, 'README.md')
    if os.path.exists(readme_src):
        shutil.copy2(readme_src, readme_dst)
        print("  已复制 README.md")
    
    # 4. 创建使用说明.md (为了方便 Windows 用户)
    usage_content = """# 🤖 Semantic Tester 使用说明

## 1. 准备工作
1. 解压本压缩包。
2. 将 `.env.config.example` 复制并重命名为 `.env.config`。
3. 编辑 `.env.config`，填入您的 API Key。
4. 在本目录下创建 `kb-docs` 文件夹，放入您的知识库文档。

## 2. 启动
双击 `semantic_tester.exe` 即可启动。

## 3. 常见问题
如果闪退，请检查配置文件是否正确，或在命令行中运行以查看错误信息。
"""
    with open(os.path.join(release_dir, '使用说明.md'), 'w', encoding='utf-8') as f:
        f.write(usage_content)
    print("  已创建 使用说明.md")

    # 5. 压缩
    print(f"正在创建 ZIP 文件: {zip_filename}")
    try:
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for root, dirs, files in os.walk(release_dir):
                for file in files:
                    file_path = os.path.join(root, file)
                    arcname = os.path.relpath(file_path, release_dir)
                    zipf.write(file_path, arcname)
                    print(f"  添加: {arcname}")
        
        print(f"\n✅ ZIP 文件创建成功: {zip_path}")
        file_size = os.path.getsize(zip_path) / (1024 * 1024)
        print(f"   文件大小: {file_size:.2f} MB")
        return True
    
    except Exception as e:
        print(f"\n❌ 创建 ZIP 文件失败: {e}")
        return False

if __name__ == '__main__':
    create_release_zip()
