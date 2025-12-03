"""
创建 Windows 发布包压缩文件
"""
import os
import zipfile
from datetime import datetime


def create_release_zip():
    """创建发布包ZIP文件"""
    # 获取当前目录（项目根目录）
    project_root = os.getcwd()
    release_dir = os.path.join(project_root, 'release_windows')
    
    if not os.path.exists(release_dir):
        print(f"错误: 发布目录不存在: {release_dir}")
        return False
    
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
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    zip_filename = f'semantic_tester_windows_v{version}_{timestamp}.zip'
    zip_path = os.path.join(project_root, zip_filename)
    
    print(f"正在创建 ZIP 文件: {zip_filename}")
    
    try:
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            # 遍历发布目录中的所有文件
            for root, dirs, files in os.walk(release_dir):
                for file in files:
                    file_path = os.path.join(root, file)
                    # 计算相对路径
                    arcname = os.path.relpath(file_path, release_dir)
                    zipf.write(file_path, arcname)
                    print(f"  添加: {arcname}")
        
        print(f"\n✅ ZIP 文件创建成功: {zip_path}")
        
        # 显示文件大小
        file_size = os.path.getsize(zip_path) / (1024 * 1024)  # MB
        print(f"   文件大小: {file_size:.2f} MB")
        
        return True
    
    except Exception as e:
        print(f"\n❌ 创建 ZIP 文件失败: {e}")
        return False


if __name__ == '__main__':
    create_release_zip()
