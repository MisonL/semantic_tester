"""
Excel 处理器

处理 Excel 文件的读取、格式检测、数据处理和保存。
"""

import logging
import os
import sys
from typing import Dict, List, Optional, Tuple, Any

import pandas as pd
from colorama import Fore, Style

from .utils import get_column_index, get_or_add_column

logger = logging.getLogger(__name__)


class ExcelProcessor:
    """Excel 文件处理器"""

    def __init__(self, excel_path: str):
        """
        初始化 Excel 处理器

        Args:
            excel_path: Excel 文件路径
        """
        self.excel_path = excel_path
        self.df: Optional[pd.DataFrame] = None
        self.column_names: List[str] = []
        self.workbook: Optional[Any] = None
        self.worksheet: Optional[Any] = None
        self.is_dify_format = False
        self.format_info: dict[str, Any] = {}

    def load_excel(self) -> bool:
        """
        加载 Excel 文件

        Returns:
            bool: 是否成功加载
        """
        try:
            # 使用 pandas 读取 Excel 文件以获取 DataFrame，指定引擎
            try:
                self.df = pd.read_excel(self.excel_path, engine="openpyxl")
            except Exception:
                self.df = pd.read_excel(self.excel_path, engine="xlrd")

            logger.info(f"正在读取Excel文件：{self.excel_path}")
            logger.info(
                f"Excel文件读取成功，共 {len(self.df)} 行 {len(self.df.columns)} 列。"
            )
            logger.info(f"列名: {list(self.df.columns)}")

            # 获取列名并转换为字符串
            self.column_names = [str(col) for col in self.df.columns]

            # 加载工作簿用于后续操作
            from openpyxl import load_workbook

            self.workbook = load_workbook(self.excel_path)
            self.worksheet = self.workbook.active

            return True
        except Exception as e:
            logger.error(f"无法读取 Excel 文件 '{self.excel_path}'：{e}")
            return False

    def detect_format(self) -> Dict:
        """
        检测 Excel 文件格式（是否为 dify_chat_tester 输出格式）

        Returns:
            Dict: 格式检测结果信息
        """
        # 检查必需的核心列
        has_question_col = any(
            col in self.column_names for col in ["原始问题", "用户输入", "问题"]
        )
        has_response_col = any(col.endswith("响应") for col in self.column_names)
        has_timestamp_col = any(
            col in self.column_names for col in ["时间戳", "Timestamp"]
        )
        has_success_col = any(
            col in self.column_names for col in ["是否成功", "成功", "Success"]
        )

        # 综合判断是否为dify格式
        # 默认期望Dify Chat Tester格式
        self.is_dify_format = (
            has_question_col and has_response_col and has_timestamp_col
        )
        
        # 如果不是Dify格式，提供转换建议
        if not self.is_dify_format:
            self._suggest_dify_format_conversion()

        format_info: dict[str, Any] = {
            "is_dify_format": self.is_dify_format,
            "has_question_col": has_question_col,
            "has_response_col": has_response_col,
            "has_timestamp_col": has_timestamp_col,
            "has_success_col": has_success_col,
            "question_col": None,
            "response_col": None,
            "response_cols": [],
        }

        if self.is_dify_format:
            # 找到问题列和响应列
            question_col = None
            response_cols = []

            # 确定问题列
            for col in ["原始问题", "用户输入", "问题"]:
                if col in self.column_names:
                    question_col = col
                    break

            # 确定响应列（以"响应"结尾的列）
            for col in self.column_names:
                if col.endswith("响应") and col != question_col:
                    response_cols.append(col)

            format_info["question_col"] = question_col
            format_info["response_cols"] = response_cols or []

            # 添加列索引信息
            if question_col:
                format_info["question_col_index"] = self.column_names.index(question_col)
            if response_cols:
                format_info["response_cols_index"] = [self.column_names.index(col) for col in response_cols]

        self.format_info = format_info
        return format_info

    def _suggest_dify_format_conversion(self):
        """建议转换为Dify Chat Tester格式"""
        from colorama import Fore, Style
        
        print(f"\n{Fore.YELLOW}⚠️  检测到非标准Dify Chat Tester格式{Style.RESET_ALL}")
        print(f"{Fore.CYAN}建议使用Dify Chat Tester标准格式以获得最佳体验：{Style.RESET_ALL}")
        print()
        print("标准格式包含以下列：")
        print("  • 时间戳")
        print("  • 角色")
        print("  • 原始问题")
        print("  • {供应商}响应 (如: Dify响应, iFlow响应等)")
        print("  • 是否成功")
        print("  • 错误信息")
        print("  • 对话ID")
        print()
        print("选项：")
        print("1. 生成Dify格式模板")
        print("2. 继续使用当前格式（可能影响功能）")
        
        choice = input(f"\n{Fore.YELLOW}请选择 (1-2，默认: 1): {Style.RESET_ALL}").strip()
        
        if choice == "2":
            print(f"{Fore.YELLOW}⚠️  将使用当前格式，某些功能可能受限{Style.RESET_ALL}")
            return
        
        # 生成Dify模板
        try:
            from .dify_template_generator import DifyTemplateGenerator
            generator = DifyTemplateGenerator()
            
            print(f"\n{Fore.GREEN}📝 正在生成Dify Chat Tester模板...{Style.RESET_ALL}")
            
            # 默认生成Dify供应商模板
            template_path = generator.generate_basic_template("dify")
            
            print(f"\n{Fore.CYAN}模板使用说明：{Style.RESET_ALL}")
            print(f"1. 模板文件已生成: {template_path}")
            print("2. 在Excel中填写您的测试问题")
            print("3. 使用Dify Chat Tester或其他工具生成AI回答")
            print("4. 保存后重新运行本程序进行语义评估")
            print()
            print(f"{Fore.GREEN}✅ 模板生成完成！{Style.RESET_ALL}")
            
        except Exception as e:
            print(f"{Fore.RED}❌ 模板生成失败: {e}{Style.RESET_ALL}")
            print(f"{Fore.YELLOW}⚠️  将继续使用当前格式{Style.RESET_ALL}")

    def display_format_info(self):
        """显示格式检测结果"""
        print("\nExcel 文件中的列名:")
        for i, col_name in enumerate(self.column_names):
            print(f"{i + 1}. {col_name}")

        if self.is_dify_format:
            print(
                f"\n{Fore.GREEN}✅ 检测到 Dify Chat Tester 输出格式！{Style.RESET_ALL}"
            )
            print("将自动适配列映射关系：")
            print(f"  • 序号 {self.format_info['question_col_index'] + 1} ({self.format_info['question_col']}) → 问题点")
            response_col = (
                self.format_info['response_cols'][0]
                if self.format_info['response_cols'] else '未知'
            )
            response_col_index = self.format_info['response_cols_index'][0] if self.format_info['response_cols_index'] else 0
            print(f"  • 序号 {response_col_index + 1} ({response_col}) → AI客服回答")
            print("  • 序号 0 (文档名称) → 需要手动指定 - 自动添加列")

    def auto_add_document_column(self):
        """自动添加文档名称列（针对 dify 格式）"""
        assert self.df is not None, "DataFrame must be loaded before adding columns"
        if "文档名称" not in self.column_names:
            self.df.insert(0, "文档名称", "")  # 在第一列插入文档名称列
            self.column_names.insert(0, "文档名称")
            print(
                f"\n{Fore.YELLOW}📝 已自动添加'文档名称'列，请稍后手动填写对应的文档名。{Style.RESET_ALL}"
            )

    def get_user_column_mapping(self, auto_config: bool = False) -> Dict[str, int]:
        """
        获取用户列映射配置

        Args:
            auto_config: 是否使用自动配置（针对 dify 格式）

        Returns:
            Dict[str, int]: 列索引映射
        """
        if auto_config and self.is_dify_format:
            column_mapping = self._auto_configure_columns()
            if column_mapping:
                return column_mapping
            # 如果自动配置失败，切换到手动配置
            logger.warning("自动配置失败，切换到手动配置")

        # 手动配置列映射
        return self._manual_configure_columns()

    def _auto_configure_columns(self) -> Optional[Dict[str, int]]:
        """
        自动配置列映射（针对 dify 格式）

        Returns:
            Optional[Dict[str, int]]: 列索引映射，如果失败返回None
        """
        doc_name_col_index = 0  # 文档名称列
        question_col_index = self.column_names.index(
            self.format_info["question_col"]
        )

        # 处理响应列选择
        response_col = self._select_response_column()
        if not response_col:
            return None

        ai_answer_col_index = self.column_names.index(response_col)

        column_mapping = {
            "doc_name_col_index": doc_name_col_index,
            "question_col_index": question_col_index,
            "ai_answer_col_index": ai_answer_col_index,
        }

        self._display_column_mapping(column_mapping)

        # 询问是否使用自动配置
        if self._confirm_auto_config():
            return column_mapping

        return None

    def _select_response_column(self) -> Optional[str]:
        """
        选择响应列

        Returns:
            Optional[str]: 选择的列名或None
        """
        response_cols = self.format_info["response_cols"]

        if not response_cols:
            print(f"{Fore.RED}❌ 未找到任何响应列！{Style.RESET_ALL}")
            return None

        if len(response_cols) == 1:
            return response_cols[0]

        print(
            f"\n{Fore.YELLOW}发现多个响应列，请选择要使用的一个：{Style.RESET_ALL}"
        )
        for i, col in enumerate(response_cols):
            print(f"  {i + 1}. {col}")

        while True:
            choice = input(
                f"请输入选择 (1-{len(response_cols)}, 默认: 1): "
            ).strip()
            if not choice:
                choice = "1"

            try:
                choice_idx = int(choice) - 1
                if 0 <= choice_idx < len(response_cols):
                    return response_cols[choice_idx]
                else:
                    print(
                        f"选择无效，请输入 1-{len(response_cols)} 之间的数字。"
                    )
            except ValueError:
                print("请输入有效的数字。")

    def _display_column_mapping(self, column_mapping: Dict[str, int]):
        """
        显示列映射配置
        """
        print("\n已配置列映射：")

        # 文档名称列 - 自动添加的列固定为序号0
        doc_col_num = 0  # 自动添加的文档名称列始终是序号0
        print(f"  • 文档名称: 序号 {doc_col_num} ('文档名称' - 自动添加)")
        
        # 问题点列 - 使用原Excel列序号
        question_col_num = column_mapping['question_col_index'] + 1
        print(f"  • 问题点: 序号 {question_col_num} ('{self.format_info['question_col']}')")

        # AI客服回答列 - 使用原Excel列序号
        response_col_name = (
            self.format_info['response_cols'][0]
            if self.format_info['response_cols'] else '未知'
        )
        ai_answer_col_num = column_mapping['ai_answer_col_index'] + 1
        print(f"  • AI客服回答: 序号 {ai_answer_col_num} ('{response_col_name}')")

    def _confirm_auto_config(self) -> bool:
        """
        确认是否使用自动配置

        Returns:
            bool: True 表示确认使用
        """
        use_auto_config = input(
            f"\n{Fore.CYAN}是否使用此自动配置？(Y/n，默认: Y): {Style.RESET_ALL}"
        ).lower()
        return use_auto_config != "n"

    def _manual_configure_columns(self) -> Dict[str, int]:
        """
        手动配置列映射

        Returns:
            Dict[str, int]: 列索引映射
        """
        # 获取"文档名称"列
        doc_name_col_index = self._get_column_index_by_input(
            "文档名称", "请输入\"文档名称\"所在列的名称或序号"
        )

        # 获取"问题点"列
        question_col_index = self._get_column_index_by_input(
            "问题点", "请输入\"问题点\"所在列的名称或序号"
        )

        # 获取"AI客服回答"列
        ai_answer_col_index = self._get_column_index_by_input(
            "AI客服回答", "请输入\"AI客服回答\"所在列的名称或序号"
        )

        return {
            "doc_name_col_index": doc_name_col_index,
            "question_col_index": question_col_index,
            "ai_answer_col_index": ai_answer_col_index,
        }

    def _get_column_index_by_input(self, column_type: str, prompt: str) -> int:
        """
        根据用户输入获取列索引

        Args:
            column_type: 列类型（用于错误消息）
            prompt: 提示信息

        Returns:
            int: 列索引
        """
        col_input = input(f"{prompt} (例如: \"{column_type}\" 或 \"1\"): ")
        col_index = get_column_index(self.column_names, col_input)

        if col_index == -1:
            logger.error(
                f"错误: 未找到列名为 '{col_input}' 的'{column_type}'列。程序退出。"
            )
            sys.exit(1)

        return col_index

    def get_result_columns(self) -> Dict[str, Tuple[str, int]]:
        """
        获取结果保存列配置

        Returns:
            Dict[str, Tuple[str, int]]: 结果列配置，包含列名和索引
        """
        assert (
            self.df is not None
        ), "DataFrame must be loaded before getting result columns"
        # --- 获取"语义是否与源文档相符"结果保存列 ---
        print("\n请选择'语义是否与源文档相符'结果保存列:")
        print("现有列:")
        for i, col_name in enumerate(self.column_names):
            # 标记自动添加的列
            marker = " [自动添加]" if i == 0 and col_name == "文档名称" else ""
            print(f"  {i}. {col_name}{marker}")
        print("  新建列: 直接输入列名")
        
        similarity_result_col_input = input(
            "请选择序号、输入列名或按回车使用默认: "
        ).strip()
        
        if not similarity_result_col_input:
            similarity_result_col_input = "语义是否与源文档相符"
        
        # 处理输入
        try:
            col_index = int(similarity_result_col_input)
            if 0 <= col_index < len(self.column_names):
                similarity_result_col_index = col_index
                print(f"✅ 选择现有列: {self.column_names[col_index]}")
            else:
                print(f"⚠️  序号超出范围，将创建新列: {similarity_result_col_input}")
                similarity_result_col_index = get_or_add_column(
                    self.df, self.column_names, similarity_result_col_input
                )
        except ValueError:
            # 输入的是列名
            similarity_result_col_index = get_or_add_column(
                self.df, self.column_names, similarity_result_col_input
            )
            print(f"✅ 使用列: {similarity_result_col_input}")

        # --- 获取"判断依据"结果保存列 ---
        print("\n请选择'判断依据'结果保存列:")
        print("现有列:")
        for i, col_name in enumerate(self.column_names):
            # 标记自动添加的列
            marker = " [自动添加]" if i == 0 and col_name == "文档名称" else ""
            print(f"  {i}. {col_name}{marker}")
        print("  新建列: 直接输入列名")
        
        reason_col_input = input(
            "请选择序号、输入列名或按回车使用默认: "
        ).strip()
        
        if not reason_col_input:
            reason_col_input = "判断依据"
        
        # 处理输入
        try:
            col_index = int(reason_col_input)
            if 0 <= col_index < len(self.column_names):
                reason_col_index = col_index
                print(f"✅ 选择现有列: {self.column_names[col_index]}")
            else:
                print(f"⚠️  序号超出范围，将创建新列: {reason_col_input}")
                reason_col_index = get_or_add_column(
                    self.df, self.column_names, reason_col_input
                )
        except ValueError:
            # 输入的是列名
            reason_col_index = get_or_add_column(
                self.df, self.column_names, reason_col_input
            )
            print(f"✅ 使用列: {reason_col_input}")

        return {
            "similarity_result": (
                similarity_result_col_input,
                similarity_result_col_index,
            ),
            "reason": (reason_col_input, reason_col_index),
        }

    def suggest_document_names(self):
        """
        智能建议文档名称填充
        
        基于文件名或对话ID等信息为文档名称列提供填充建议
        """
        if "文档名称" not in self.column_names:
            return
            
        # 检查文档名称列是否为空
        doc_col_empty = self.df["文档名称"].isna().all() or (self.df["文档名称"] == "").all()
        
        if not doc_col_empty:
            return  # 已经有内容，不需要建议
            
        print(f"\n{Fore.YELLOW}📝 检测到'文档名称'列为空，建议填充方式：{Style.RESET_ALL}")
        print("1. 使用文件名作为文档名")
        print("2. 使用统一文档名（手动输入）")
        print("3. 跳过填充（稍后手动填写）")
        
        choice = input(f"\n{Fore.YELLOW}请选择 (1-3，默认: 3): {Style.RESET_ALL}").strip()
        
        if choice == "1":
            # 使用文件名作为文档名
            file_name = os.path.splitext(os.path.basename(self.file_path))[0]
            self.df["文档名称"] = file_name
            print(f"✅ 已将所有行的文档名称设置为: {file_name}")
            
        elif choice == "2":
            # 使用统一文档名
            doc_name = input(f"{Fore.YELLOW}请输入文档名称: {Style.RESET_ALL}").strip()
            if doc_name:
                self.df["文档名称"] = doc_name
                print(f"✅ 已将所有行的文档名称设置为: {doc_name}")
            else:
                print("⚠️  文档名称为空，跳过填充")
        else:
            print("ℹ️  跳过文档名称填充，请稍后手动填写")

    def setup_result_columns(self, result_columns: Dict[str, Tuple[str, int]]):
        """
        设置结果列的数据类型

        Args:
            result_columns: 结果列配置
        """
        assert (
            self.df is not None
        ), "DataFrame must be loaded before setting up result columns"
        similarity_col_name = result_columns["similarity_result"][0]
        reason_col_name = result_columns["reason"][0]

        # 检查结果列是否存在，如果不存在则创建，并指定dtype为object
        if similarity_col_name not in self.df.columns:
            self.df[similarity_col_name] = pd.Series(dtype="object")
        if reason_col_name not in self.df.columns:
            self.df[reason_col_name] = pd.Series(dtype="object")

        # 强制转换列的dtype为object，确保能够存储字符串，解决FutureWarning
        self.df[similarity_col_name] = self.df[similarity_col_name].astype("object")
        self.df[reason_col_name] = self.df[reason_col_name].astype("object")

    def get_row_data(
        self, row_index: int, column_mapping: Dict[str, int]
    ) -> Dict[str, str]:
        """
        获取指定行的数据

        Args:
            row_index: 行索引
            column_mapping: 列映射配置

        Returns:
            Dict[str, str]: 行数据
        """
        assert self.df is not None, "DataFrame must be loaded before getting row data"
        row = self.df.iloc[row_index]

        doc_name_col_index = column_mapping["doc_name_col_index"]
        question_col_index = column_mapping["question_col_index"]
        ai_answer_col_index = column_mapping["ai_answer_col_index"]

        doc_name = (
            str(row.iloc[doc_name_col_index]).strip()
            if pd.notna(row.iloc[doc_name_col_index])
            else "未知文档"
        )
        question = (
            str(row.iloc[question_col_index]).strip()
            if pd.notna(row.iloc[question_col_index])
            else ""
        )
        ai_answer = (
            str(row.iloc[ai_answer_col_index]).strip()
            if pd.notna(row.iloc[ai_answer_col_index])
            else ""
        )

        return {"doc_name": doc_name, "question": question, "ai_answer": ai_answer}

    def save_result(
        self,
        row_index: int,
        result: str,
        reason: str,
        result_columns: Dict[str, Tuple[str, int]],
    ):
        """
        保存结果到指定行

        Args:
            row_index: 行索引
            result: 语义比对结果
            reason: 判断依据
            result_columns: 结果列配置
        """
        assert self.df is not None, "DataFrame must be loaded before saving results"
        similarity_col_name = result_columns["similarity_result"][0]
        reason_col_name = result_columns["reason"][0]

        self.df.at[row_index, similarity_col_name] = result
        self.df.at[row_index, reason_col_name] = reason

    def save_intermediate_results(self, output_path: str, processed_count: int):
        """
        保存中间结果

        Args:
            output_path: 输出文件路径
            processed_count: 已处理的记录数
        """
        assert (
            self.df is not None
        ), "DataFrame must be loaded before saving intermediate results"
        try:
            self.df.to_excel(output_path, index=False)
            logger.info(
                f"已保存中间结果到 {output_path} (已处理 {processed_count} 条记录)。"
            )
        except Exception as e:
            logger.error(f"保存中间结果失败: {e}")

    def save_final_results(self, output_path: str):
        """
        保存最终结果

        Args:
            output_path: 输出文件路径
        """
        assert (
            self.df is not None
        ), "DataFrame must be loaded before saving final results"
        try:
            self.df.to_excel(output_path, index=False)
            logger.info(f"最终结果已保存到 {output_path}")
        except Exception as e:
            logger.error(f"保存最终结果失败: {e}")

    def get_total_records(self) -> int:
        """
        获取总记录数

        Returns:
            int: 总记录数
        """
        return len(self.df) if self.df is not None else 0

    def validate_file_exists(self) -> bool:
        """
        验证文件是否存在

        Returns:
            bool: 文件是否存在
        """
        return os.path.exists(self.excel_path)
