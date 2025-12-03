"""
格式化工具

提供各种格式化功能的工具函数。
"""

import re
import textwrap
from typing import Dict, List, Optional


class FormatUtils:
    """格式化工具类"""

    @staticmethod
    def truncate_text(text: str, max_length: int, suffix: str = "...") -> str:
        """
        截断文本到指定长度

        Args:
            text: 原文本
            max_length: 最大长度
            suffix: 截断后缀

        Returns:
            str: 截断后的文本
        """
        if not text or len(text) <= max_length:
            return text

        return text[: max_length - len(suffix)] + suffix

    @staticmethod
    def clean_text(text: str) -> str:
        """
        清理文本（移除多余空白字符）

        Args:
            text: 原文本

        Returns:
            str: 清理后的文本
        """
        if not text:
            return ""

        # 移除首尾空白
        text = text.strip()

        # 将多个连续的空白字符替换为单个空格
        text = re.sub(r"\s+", " ", text)

        return text

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
    def format_duration(seconds: float) -> str:
        """
        格式化时间长度

        Args:
            seconds: 秒数

        Returns:
            str: 格式化的时间长度
        """
        if seconds < 1:
            return f"{int(seconds * 1000)}ms"
        elif seconds < 60:
            return f"{seconds:.1f}s"
        elif seconds < 3600:
            minutes = int(seconds // 60)
            remaining_seconds = int(seconds % 60)
            return f"{minutes}m {remaining_seconds}s"
        else:
            hours = int(seconds // 3600)
            remaining_minutes = int((seconds % 3600) // 60)
            return f"{hours}h {remaining_minutes}m"

    @staticmethod
    def format_percentage(value: float, total: float, decimal_places: int = 1) -> str:
        """
        格式化百分比

        Args:
            value: 当前值
            total: 总值
            decimal_places: 小数位数

        Returns:
            str: 格式化的百分比
        """
        if total == 0:
            return "0.0%"

        percentage = (value / total) * 100
        return f"{percentage:.{decimal_places}f}%"

    @staticmethod
    def wrap_text(text: str, width: int = 80, indent: str = "") -> List[str]:
        """
        文本换行

        Args:
            text: 原文本
            width: 行宽
            indent: 缩进

        Returns:
            List[str]: 换行后的文本行列表
        """
        if not text:
            return []

        wrapped_lines = textwrap.wrap(
            text, width=width, initial_indent=indent, subsequent_indent=indent
        )
        return wrapped_lines

    @staticmethod
    def format_table(
        data: List[List[str]], headers: Optional[List[str]] = None, max_width: int = 20
    ) -> str:
        """
        格式化表格

        Args:
            data: 表格数据
            headers: 表头
            max_width: 单元格最大宽度

        Returns:
            str: 格式化的表格字符串
        """
        if not data:
            return ""

        # 计算列宽
        all_rows = data[:]
        if headers:
            all_rows.insert(0, headers)

        col_widths = []
        for col_idx in range(len(all_rows[0])):
            max_col_width = max(len(str(row[col_idx])) for row in all_rows)
            col_widths.append(min(max_col_width, max_width))

        # 格式化每一行
        formatted_rows = []
        for row in all_rows:
            formatted_cells = []
            for col_idx, cell in enumerate(row):
                cell_str = str(cell)
                if len(cell_str) > col_widths[col_idx]:
                    cell_str = cell_str[: col_widths[col_idx] - 3] + "..."
                formatted_cells.append(cell_str.ljust(col_widths[col_idx]))
            formatted_rows.append(" | ".join(formatted_cells))

        # 添加分隔线
        if headers:
            separator = "-+-".join("-" * width for width in col_widths)
            formatted_rows.insert(1, separator)

        return "\n".join(formatted_rows)

    @staticmethod
    def format_number(number: int) -> str:
        """
        格式化数字（添加千位分隔符）

        Args:
            number: 数字

        Returns:
            str: 格式化的数字字符串
        """
        return f"{number:,}"

    @staticmethod
    def format_api_key_preview(
        api_key: str, prefix_chars: int = 5, suffix_chars: int = 4
    ) -> str:
        """
        格式化 API 密钥预览

        Args:
            api_key: API 密钥
            prefix_chars: 前缀字符数
            suffix_chars: 后缀字符数

        Returns:
            str: 格式化的 API 密钥预览
        """
        if not api_key:
            return "无"

        if len(api_key) <= prefix_chars + suffix_chars + 3:
            return api_key[:3] + "..."

        return f"{api_key[:prefix_chars]}...{api_key[-suffix_chars:]}"

    @staticmethod
    def clean_json_text(text: str) -> str:
        """
        清理 JSON 文本（移除 Markdown 代码块标记）

        Args:
            text: 原文本

        Returns:
            str: 清理后的 JSON 文本
        """
        if not text:
            return ""

        # 移除 Markdown 代码块标记
        if text.startswith("```json") and text.endswith("```"):
            text = text[7:-3].strip()
        elif text.startswith("```") and text.endswith("```"):
            text = text[3:-3].strip()

        return text

    @staticmethod
    def highlight_keywords(
        text: str, keywords: List[str], color_code: str = "\033[91m"
    ) -> str:
        """
        高亮文本中的关键词

        Args:
            text: 原文本
            keywords: 关键词列表
            color_code: ANSI 颜色代码

        Returns:
            str: 高亮后的文本
        """
        if not text or not keywords:
            return text

        reset_code = "\033[0m"
        highlighted_text = text

        for keyword in keywords:
            if keyword:  # 确保关键词不为空
                # 使用不区分大小写的替换
                pattern = re.compile(re.escape(keyword), re.IGNORECASE)

                # 用匹配到的整个关键词（group 0）包裹颜色代码
                highlighted_text = pattern.sub(
                    lambda m: f"{color_code}{m.group(0)}{reset_code}",
                    highlighted_text,
                )

        return highlighted_text

    @staticmethod
    def extract_error_details(error_message: str) -> Dict[str, str]:
        """
        从错误消息中提取详细信息

        Args:
            error_message: 错误消息

        Returns:
            Dict[str, str]: 提取的错误详情
        """
        details = {"type": "未知错误", "message": error_message, "retry_delay": ""}

        # 尝试提取重试延迟
        retry_match = re.search(r"'retryDelay': '(\d+)s'", error_message)
        if retry_match:
            details["retry_delay"] = retry_match.group(1) + "s"

        # 尝试提取错误类型
        if "429" in error_message or "ResourceExhausted" in error_message:
            details["type"] = "速率限制错误"
        elif "JSON" in error_message:
            details["type"] = "JSON 解析错误"
        elif (
            "network" in error_message.lower() or "connection" in error_message.lower()
        ):
            details["type"] = "网络连接错误"
        elif (
            "permission" in error_message.lower()
            or "unauthorized" in error_message.lower()
        ):
            details["type"] = "权限错误"

        return details
