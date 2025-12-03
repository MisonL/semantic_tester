"""
验证工具

提供各种验证功能的工具函数。
"""

import os
import re
from typing import List, Dict, Any, Optional


class ValidationUtils:
    """验证工具类"""

    @staticmethod
    def is_valid_file_path(
        file_path: str, extensions: Optional[List[str]] = None
    ) -> bool:
        """
        验证文件路径是否有效

        Args:
            file_path: 文件路径
            extensions: 允许的文件扩展名列表

        Returns:
            bool: 是否有效
        """
        if not file_path or not isinstance(file_path, str):
            return False

        if not os.path.isfile(file_path):
            return False

        if extensions:
            file_ext = os.path.splitext(file_path)[1].lower()
            if file_ext not in [ext.lower() for ext in extensions]:
                return False

        return True

    @staticmethod
    def is_valid_directory_path(dir_path: str) -> bool:
        """
        验证目录路径是否有效

        Args:
            dir_path: 目录路径

        Returns:
            bool: 是否有效
        """
        if not dir_path or not isinstance(dir_path, str):
            return False

        return os.path.isdir(dir_path)

    @staticmethod
    def is_valid_gemini_api_key(api_key: str) -> bool:
        """
        验证 Gemini API 密钥格式

        Args:
            api_key: API 密钥

        Returns:
            bool: 是否有效格式
        """
        if not api_key or not isinstance(api_key, str):
            return False

        # Gemini API 密钥通常是字母、数字、下划线和连字符的组合，长度至少20个字符
        pattern = r"^[a-zA-Z0-9_-]{20,}$"
        return bool(re.match(pattern, api_key))

    @staticmethod
    def validate_column_mapping(
        column_mapping: Dict[str, int], total_columns: int
    ) -> List[str]:
        """
        验证列映射配置

        Args:
            column_mapping: 列映射字典
            total_columns: 总列数

        Returns:
            List[str]: 错误信息列表，空列表表示验证通过
        """
        errors = []

        if not column_mapping:
            errors.append("列映射不能为空")
            return errors

        required_keys = [
            "doc_name_col_index",
            "question_col_index",
            "ai_answer_col_index",
        ]
        for key in required_keys:
            if key not in column_mapping:
                errors.append(f"缺少必需的列映射: {key}")

        for key, index in column_mapping.items():
            if not isinstance(index, int):
                errors.append(f"列索引必须是整数: {key}")
            elif index < 0 or index >= total_columns:
                errors.append(
                    f"列索引超出范围: {key} = {index} (范围: 0-{total_columns - 1})"
                )

        # 检查是否有重复的列索引
        indices = list(column_mapping.values())
        if len(indices) != len(set(indices)):
            errors.append("列映射中有重复的列索引")

        return errors

    @staticmethod
    def validate_excel_file(file_path: str) -> List[str]:
        """
        验证 Excel 文件

        Args:
            file_path: Excel 文件路径

        Returns:
            List[str]: 错误信息列表，空列表表示验证通过
        """
        errors = []

        if not ValidationUtils.is_valid_file_path(file_path, [".xlsx", ".xls"]):
            errors.append("文件不存在或不是有效的 Excel 文件")
            return errors

        try:
            import pandas as pd

            # 尝试读取文件
            try:
                df = pd.read_excel(file_path, engine="openpyxl")
            except Exception:
                df = pd.read_excel(file_path, engine="xlrd")

            if df.empty:
                errors.append("Excel 文件为空")
            elif len(df.columns) < 3:
                errors.append(
                    "Excel 文件至少需要包含 3 列（文档名称、问题点、AI客服回答）"
                )

        except Exception as e:
            errors.append(f"无法读取 Excel 文件: {str(e)}")

        return errors

    @staticmethod
    def validate_knowledge_base_directory(dir_path: str) -> List[str]:
        """
        验证知识库目录

        Args:
            dir_path: 知识库目录路径

        Returns:
            List[str]: 错误信息列表，空列表表示验证通过
        """
        errors = []

        if not ValidationUtils.is_valid_directory_path(dir_path):
            errors.append("目录不存在或无效")
            return errors

        # 检查是否包含 Markdown 文件
        md_files = []
        try:
            for root, dirs, files in os.walk(dir_path):
                for file in files:
                    if file.lower().endswith(".md"):
                        md_files.append(os.path.join(root, file))
        except Exception as e:
            errors.append(f"读取目录时出错: {str(e)}")
            return errors

        if not md_files:
            errors.append("目录中未找到 Markdown 文件 (.md)")

        return errors

    @staticmethod
    def validate_email(email: str) -> bool:
        """
        验证邮箱地址格式

        Args:
            email: 邮箱地址

        Returns:
            bool: 是否有效
        """
        if not email:
            return False

        pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
        return bool(re.match(pattern, email))

    @staticmethod
    def validate_url(url: str) -> bool:
        """
        验证 URL 格式

        Args:
            url: URL 地址

        Returns:
            bool: 是否有效
        """
        if not url:
            return False

        pattern = r"^https?://(?:[-\w.])+(?:[:\d]+)?(?:/(?:[\w/_.])*(?:\?(?:[\w&=%.])*)?(?:#(?:\w*))?)?$"
        return bool(re.match(pattern, url))

    @staticmethod
    def validate_numeric_range(
        value: Any, min_val: Optional[float] = None, max_val: Optional[float] = None
    ) -> bool:
        """
        验证数值范围

        Args:
            value: 要验证的值
            min_val: 最小值
            max_val: 最大值

        Returns:
            bool: 是否在有效范围内
        """
        try:
            num_value = float(value)
        except (ValueError, TypeError):
            return False

        if min_val is not None and num_value < min_val:
            return False

        if max_val is not None and num_value > max_val:
            return False

        return True

    @staticmethod
    def validate_string_length(
        text: str, min_length: int = 0, max_length: Optional[int] = None
    ) -> bool:
        """
        验证字符串长度

        Args:
            text: 字符串
            min_length: 最小长度
            max_length: 最大长度

        Returns:
            bool: 长度是否有效
        """
        if not isinstance(text, str):
            return False

        length = len(text)

        if length < min_length:
            return False

        if max_length is not None and length > max_length:
            return False

        return True

    @staticmethod
    def validate_required_fields(
        data: Dict[str, Any], required_fields: List[str]
    ) -> List[str]:
        """
        验证必需字段

        Args:
            data: 数据字典
            required_fields: 必需字段列表

        Returns:
            List[str]: 缺失的字段列表
        """
        missing_fields = []

        for field in required_fields:
            if field not in data or data[field] is None or data[field] == "":
                missing_fields.append(field)

        return missing_fields

    @staticmethod
    def sanitize_filename(filename: str) -> str:
        """
        清理文件名（移除不安全字符）

        Args:
            filename: 原文件名

        Returns:
            str: 清理后的文件名
        """
        if not filename:
            return "unnamed"

        # 移除或替换不安全字符
        unsafe_chars = '<>:"/\\|?*'
        sanitized = filename

        for char in unsafe_chars:
            sanitized = sanitized.replace(char, "_")

        # 移除控制字符
        sanitized = re.sub(r"[\x00-\x1f\x7f-\x9f]", "", sanitized)

        # 移除首尾的空格和点
        sanitized = sanitized.strip(" .")

        # 确保不为空
        if not sanitized:
            sanitized = "unnamed"

        return sanitized

    @staticmethod
    def validate_row_data(row_data: Dict[str, str]) -> List[str]:
        """
        验证行数据

        Args:
            row_data: 行数据字典

        Returns:
            List[str]: 错误信息列表
        """
        errors = []

        if not row_data.get("question", "").strip():
            errors.append("问题内容为空")

        if not row_data.get("ai_answer", "").strip():
            errors.append("AI回答内容为空")

        # 文档名称允许为空，为空时会读取整个知识库文件夹
        # doc_name = row_data.get("doc_name", "").strip()
        # if not doc_name:
        #     errors.append("文档名称为空")

        return errors
