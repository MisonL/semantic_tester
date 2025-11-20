"""
文件操作工具

提供文件和目录操作的工具函数。
"""

import logging
import os
from typing import List, Optional

logger = logging.getLogger(__name__)


class FileUtils:
    """文件操作工具类"""

    @staticmethod
    def ensure_directory_exists(directory: str) -> bool:
        """
        确保目录存在，如果不存在则创建

        Args:
            directory: 目录路径

        Returns:
            bool: 是否成功（目录存在或创建成功）
        """
        if not directory:
            return False

        if os.path.exists(directory):
            return os.path.isdir(directory)

        try:
            os.makedirs(directory, exist_ok=True)
            logger.info(f"创建目录: {directory}")
            return True
        except Exception as e:
            logger.error(f"创建目录失败: {directory}, 错误: {e}")
            return False

    @staticmethod
    def find_markdown_files(directory: str, recursive: bool = True) -> List[str]:
        """
        查找目录中的 Markdown 文件

        Args:
            directory: 搜索目录
            recursive: 是否递归搜索

        Returns:
            List[str]: Markdown 文件路径列表
        """
        if not os.path.isdir(directory):
            logger.warning(f"目录不存在: {directory}")
            return []

        markdown_files = []

        if recursive:
            for root, dirs, files in os.walk(directory):
                for file in files:
                    if file.lower().endswith(".md"):
                        file_path = os.path.join(root, file)
                        markdown_files.append(file_path)
        else:
            for file in os.listdir(directory):
                if file.lower().endswith(".md"):
                    file_path = os.path.join(directory, file)
                    if os.path.isfile(file_path):
                        markdown_files.append(file_path)

        logger.info(f"在 {directory} 中找到 {len(markdown_files)} 个 Markdown 文件")
        return markdown_files

    @staticmethod
    def read_file_content(file_path: str, encoding: str = "utf-8") -> Optional[str]:
        """
        读取文件内容

        Args:
            file_path: 文件路径
            encoding: 文件编码

        Returns:
            Optional[str]: 文件内容，读取失败返回 None
        """
        if not os.path.isfile(file_path):
            logger.warning(f"文件不存在: {file_path}")
            return None

        try:
            with open(file_path, "r", encoding=encoding) as f:
                content = f.read()
            logger.debug(f"成功读取文件: {file_path} ({len(content)} 字符)")
            return content
        except Exception as e:
            logger.error(f"读取文件失败: {file_path}, 错误: {e}")
            return None

    @staticmethod
    def find_file_by_name(
        directory: str, filename: str, recursive: bool = True
    ) -> Optional[str]:
        """
        在目录中查找指定名称的文件

        Args:
            directory: 搜索目录
            filename: 文件名
            recursive: 是否递归搜索（默认True，与原始行为兼容时为False）

        Returns:
            Optional[str]: 文件路径，未找到返回 None
        """
        if not os.path.isdir(directory):
            return None

        # 首先尝试直接查找（保持与原始代码一致的行为）
        direct_path = os.path.join(directory, filename)
        if os.path.isfile(direct_path):
            return direct_path

        # 如果启用递归搜索，则在子目录中查找
        if recursive:
            for root, dirs, files in os.walk(directory):
                for file in files:
                    if file == filename:
                        found_path = os.path.join(root, file)
                        logger.debug(f"在子目录中找到文件: {filename} -> {found_path}")
                        return found_path

        logger.warning(f"未找到文件: {filename}")
        return None

    @staticmethod
    def get_file_size(file_path: str) -> int:
        """
        获取文件大小

        Args:
            file_path: 文件路径

        Returns:
            int: 文件大小（字节），文件不存在返回 0
        """
        if not os.path.isfile(file_path):
            return 0

        try:
            return os.path.getsize(file_path)
        except Exception as e:
            logger.error(f"获取文件大小失败: {file_path}, 错误: {e}")
            return 0

    @staticmethod
    def format_file_size(size_bytes: int) -> str:
        """
        格式化文件大小

        Args:
            size_bytes: 文件大小（字节）

        Returns:
            str: 格式化的文件大小
        """
        if size_bytes == 0:
            return "0 B"

        size_names = ["B", "KB", "MB", "GB", "TB"]
        i = 0
        size = float(size_bytes)

        while size >= 1024.0 and i < len(size_names) - 1:
            size /= 1024.0
            i += 1

        return f"{size:.1f} {size_names[i]}"

    @staticmethod
    def backup_file(file_path: str, backup_suffix: str = ".bak") -> bool:
        """
        备份文件

        Args:
            file_path: 原文件路径
            backup_suffix: 备份文件后缀

        Returns:
            bool: 是否备份成功
        """
        if not os.path.isfile(file_path):
            logger.warning(f"文件不存在，无法备份: {file_path}")
            return False

        backup_path = file_path + backup_suffix

        # 如果备份文件已存在，添加时间戳
        if os.path.exists(backup_path):
            import time

            timestamp = int(time.time())
            name, ext = os.path.splitext(file_path)
            backup_path = f"{name}_{timestamp}{ext}{backup_suffix}"

        try:
            import shutil

            shutil.copy2(file_path, backup_path)
            logger.info(f"文件备份成功: {file_path} -> {backup_path}")
            return True
        except Exception as e:
            logger.error(f"文件备份失败: {file_path}, 错误: {e}")
            return False

    @staticmethod
    def safe_filename(filename: str) -> str:
        """
        生成安全的文件名（移除或替换非法字符）

        Args:
            filename: 原文件名

        Returns:
            str: 安全的文件名
        """
        # 定义非法字符
        illegal_chars = '<>:"/\\|?*'

        # 替换非法字符
        safe_name = filename
        for char in illegal_chars:
            safe_name = safe_name.replace(char, "_")

        # 移除多余的空格和点
        safe_name = safe_name.strip(" .")

        # 确保不为空
        if not safe_name:
            safe_name = "unnamed_file"

        return safe_name

    @staticmethod
    def get_relative_path(file_path: str, base_path: str) -> str:
        """
        获取相对路径

        Args:
            file_path: 文件路径
            base_path: 基础路径

        Returns:
            str: 相对路径
        """
        try:
            return os.path.relpath(file_path, base_path)
        except ValueError:
            # 如果无法计算相对路径，返回原路径
            return file_path
