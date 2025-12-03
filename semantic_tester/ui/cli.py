"""
命令行界面处理

提供命令行交互功能。
"""

import logging
import os
import sys
from typing import List, Optional

from colorama import Fore, Style

# 导入终端UI美化模块
from semantic_tester.ui.terminal_ui import (
    print_success,
    print_error,
    print_warning,
    print_info,
    print_input_prompt,
    print_provider_table,
    print_file_table,
    print_comparison_result_panel,
    print_summary_panel,
    confirm,
)

logger = logging.getLogger(__name__)


class CLIInterface:
    """命令行界面处理器"""

    @staticmethod
    def print_header():
        """打印程序标题"""
        print("\n--- AI客服问答语义比对工具 (支持多AI供应商) ---")

    @staticmethod
    def select_ai_provider(provider_manager):
        """
        选择 AI 供应商

        Args:
            provider_manager: 供应商管理器实例

        Returns:
            str: 选择的供应商 ID
        """
        if not provider_manager:
            logger.error("供应商管理器未初始化")
            return None

        providers = provider_manager.get_available_providers()
        if not providers:
            print_error("❌ 没有可用的 AI 供应商")
            return None

        # 获取已配置的供应商
        configured_providers = provider_manager.get_configured_providers()

        CLIInterface._show_provider_list(providers, configured_providers)

        # 如果没有已配置的供应商，询问是否继续
        if not configured_providers:
            if not CLIInterface._confirm_unconfigured_selection():
                return None

        # 获取用户选择
        return CLIInterface._get_user_choice(provider_manager, providers)

    @staticmethod
    def _show_provider_list(providers: list, configured_providers: list):
        """
        显示供应商列表（使用美化的表格）
        """
        print_provider_table(providers, configured_providers)

    @staticmethod
    def _confirm_unconfigured_selection() -> bool:
        """
        确认是否选择未配置的供应商

        Returns:
            bool: True 表示继续，False 表示取消
        """
        print_warning("警告: 没有已配置的 AI 供应商")
        return confirm("是否继续选择未配置的供应商?", default=False)

    @staticmethod
    def _get_user_choice(provider_manager, providers: list):
        """
        获取用户选择

        Returns:
            str: 选择的供应商 ID
        """
        choices = [p["id"] for p in providers]

        while True:
            try:
                choice = print_input_prompt("请输入供应商序号 (0 退出)")
                if choice == "0":
                    print_info("用户取消操作")
                    sys.exit(0)

                # 尝试使用索引选择
                try:
                    provider_index = int(choice) - 1
                    if 0 <= provider_index < len(providers):
                        selected_id = providers[provider_index]["id"]
                        if provider_manager.set_current_provider(selected_id):
                            print_success(
                                f"已选择供应商: {providers[provider_index]['name']}"
                            )
                            return selected_id
                        else:
                            print_error("切换供应商失败，请重试")
                            continue
                    else:
                        print_error(f"无效的序号，请输入 1-{len(providers)}")
                except ValueError:
                    # 尝试使用ID选择
                    if choice in choices:
                        if provider_manager.set_current_provider(choice):
                            provider_info = next(
                                (p for p in providers if p["id"] == choice), None
                            )
                            if provider_info:
                                print_success(f"已选择供应商: {provider_info['name']}")
                            return choice
                        else:
                            print_error("切换供应商失败，请重试")
                    else:
                        print_error("无效的输入，请重新输入")

            except KeyboardInterrupt:
                print_warning("\n用户取消操作")
                sys.exit(0)

    @staticmethod
    def _use_current_provider(provider_manager):
        """
        使用当前供应商

        Returns:
            str: 当前供应商 ID 或 None
        """
        current_provider = provider_manager.get_current_provider()
        if current_provider:
            print_success(f"使用当前供应商: {current_provider.name}")
            return provider_manager.current_provider_id
        else:
            print_error("没有当前供应商")
            return None

    @staticmethod
    def _confirm_unconfigured_provider(provider) -> bool:
        """
        确认选择未配置的供应商

        Returns:
            bool: True 表示确认，False 表示取消
        """
        print_warning(f"供应商 {provider.name} 未配置，可能无法正常使用")
        return confirm("确认选择此供应商?", default=False)

    @staticmethod
    def show_provider_status(provider_manager):
        """
        显示供应商状态

        Args:
            provider_manager: 供应商管理器实例
        """
        if not provider_manager:
            print_error("供应商管理器未初始化")
            return

        provider_manager.print_provider_status()

    @staticmethod
    def configure_api_keys_interactive(env_manager):
        """
        交互式配置 API 密钥

        Args:
            env_manager: 环境管理器实例
        """
        print_info("=== API 密钥配置 ===")
        print_info("选择要配置的 AI 供应商:")

        choices = ["1. Gemini", "2. OpenAI", "3. Dify", "4. 返回上级菜单"]

        for choice in choices:
            print(choice)

        while True:
            try:
                selection = print_input_prompt("请选择 (1-4)")

                if selection == "1":
                    CLIInterface._configure_gemini_keys(env_manager)
                elif selection == "2":
                    CLIInterface._configure_openai_keys(env_manager)
                elif selection == "3":
                    CLIInterface._configure_dify_keys(env_manager)
                elif selection == "4":
                    break
                else:
                    print_error("无效选择，请输入 1-4")
            except KeyboardInterrupt:
                print_warning("\n操作已取消")
                break

    @staticmethod
    def _configure_gemini_keys(env_manager):
        """配置 Gemini API 密钥"""
        print_info("--- Gemini API 密钥配置 ---")
        print("获取 API 密钥: https://aistudio.google.com/app/apikey")

        keys_input = print_input_prompt("请输入 Gemini API 密钥 (多个密钥用逗号分隔)")
        if keys_input:
            # 设置环境变量
            import os

            os.environ["GEMINI_API_KEY"] = keys_input
            print_success("Gemini API 密钥已设置（当前会话有效）")
            print_info(
                "提示: 要永久保存，请在 .env.config 文件中配置或设置系统环境变量"
            )

    @staticmethod
    def _configure_openai_keys(env_manager):
        """配置 OpenAI API 密钥"""
        print_info("--- OpenAI API 密钥配置 ---")
        print("获取 API 密钥: https://platform.openai.com/api-keys")

        api_key = print_input_prompt("请输入 OpenAI API 密钥")
        if api_key:
            import os

            os.environ["OPENAI_API_KEY"] = api_key
            print_success("OpenAI API 密钥已设置（当前会话有效）")
            print_info(
                "提示: 要永久保存，请在 .env.config 文件中配置或设置系统环境变量"
            )

    @staticmethod
    def _configure_dify_keys(env_manager):
        """配置 Dify API 密钥"""
        print_info("--- Dify API 密钥配置 ---")
        print("获取 API 密钥: 从 Dify 工作台获取")

        api_key = print_input_prompt("请输入 Dify API 密钥")
        if api_key:
            import os

            os.environ["DIFY_API_KEY"] = api_key
            print_success("Dify API 密钥已设置（当前会话有效）")
            print_info(
                "提示: 要永久保存，请在 .env.config 文件中配置或设置系统环境变量"
            )

    @staticmethod
    def get_excel_file() -> str:
        """
        获取用户输入的 Excel 文件路径

        Returns:
            str: Excel 文件路径
        """
        while True:
            # 每次循环都重新扫描目录，确保文件列表是最新的
            excel_files = CLIInterface._get_local_excel_files()

            # 获取用户输入的文件路径
            excel_path = CLIInterface._get_user_file_input(excel_files)
            if excel_path is None:
                continue

            # 验证文件存在性
            if not CLIInterface._validate_file_exists(excel_path):
                # 文件不存在，继续循环会重新扫描目录
                continue

            # 验证文件格式
            if CLIInterface._validate_excel_format(excel_path):
                return excel_path

    @staticmethod
    def _get_local_excel_files() -> list:
        """
        获取当前目录下的Excel文件列表

        Returns:
            list: Excel文件列表
        """
        return [f for f in os.listdir(".") if f.endswith(".xlsx") and os.path.isfile(f)]

    @staticmethod
    def _get_user_file_input(excel_files: list) -> Optional[str]:
        """
        获取用户输入的文件路径

        Args:
            excel_files: Excel文件列表

        Returns:
            str: 文件路径
        """
        if excel_files:
            # 使用更明确的标题说明这是问答记录表
            print_file_table(excel_files, title="问答记录表文件")

            while True:
                try:
                    choice = print_input_prompt(
                        f"请选择问答记录表序号 (1-{len(excel_files)}) 或直接输入文件路径"
                    )

                    # 尝试解析为序号
                    try:
                        index = int(choice) - 1
                        if 0 <= index < len(excel_files):
                            selected_file = excel_files[index]
                            print_success(f"已选择文件: {selected_file}")
                            return selected_file
                    except ValueError:
                        pass

                    # 如果不是序号，则作为路径返回
                    if choice:
                        return choice

                except KeyboardInterrupt:
                    print_warning("\n操作已取消")
                    sys.exit(0)
        else:
            print_warning("当前目录没有找到 Excel 文件")
            return print_input_prompt("请输入问答记录表文件路径")

    @staticmethod
    def _validate_file_exists(excel_path: str) -> bool:
        """
        验证文件是否存在

        Args:
            excel_path: 文件路径

        Returns:
            bool: 文件存在返回True
        """
        if not os.path.exists(excel_path):
            print_error(f"文件不存在: {excel_path}")
            return False
        return True

    @staticmethod
    def _validate_excel_format(excel_path: str) -> bool:
        """
        验证Excel文件格式

        Args:
            excel_path: 文件路径

        Returns:
            bool: 格式正确返回True
        """
        try:
            import pandas as pd

            try:
                pd.read_excel(excel_path, engine="openpyxl")
            except Exception:
                pd.read_excel(excel_path, engine="xlrd")
            return True
        except Exception as e:
            print(
                f"错误: 无法读取 Excel 文件 '{excel_path}'。请确保文件格式正确且未被占用。错误信息: {e}。请重新输入。",
                file=sys.stderr,
            )
            return False

    @staticmethod
    def get_knowledge_base_dir() -> str:
        """
        获取知识库目录路径

        Returns:
            str: 知识库目录路径
        """
        default_path = "./kb-docs/"
        if os.path.isdir(default_path):
            print_info(f"检测到默认知识库目录: {default_path}")
            if CLIInterface.get_confirmation("是否使用此目录?", default=True):
                return default_path

        while True:
            path = print_input_prompt("请输入知识库文档目录路径")
            if not path:
                # 如果用户直接回车且默认目录存在，则使用默认目录
                if os.path.isdir(default_path):
                    return default_path
                print_error("知识库目录路径不能为空。")
                continue

            if os.path.isdir(path):
                print_success(f"已选择知识库目录: {path}")
                return path
            else:
                print_error(f"目录不存在: {path}")
                continue

    @staticmethod
    def get_output_path(default_path: str) -> str:
        """
        获取输出文件路径

        Args:
            default_path: 默认输出路径

        Returns:
            str: 输出文件路径
        """
        default_output_path = default_path
        print_info(f"默认输出路径: {default_output_path}")
        if CLIInterface.get_confirmation("是否使用默认输出路径?", default=True):
            return default_output_path

        while True:
            path = print_input_prompt("请输入输出文件路径")
            if path:
                if not path.endswith(".xlsx"):
                    path += ".xlsx"
                print_success(f"已设置输出路径: {path}")
                return path
            else:
                print_error("输出文件路径不能为空。")

    @staticmethod
    def ask_show_comparison_result() -> bool:
        """
        询问是否在控制台显示比对结果

        Returns:
            bool: 是否显示比对结果
        """
        display_result_choice = input(
            "是否在控制台显示每个问题的比对结果？ (Y/n，默认: Y): "
        ).lower()
        return display_result_choice != "n"

    @staticmethod
    def confirm_auto_config() -> bool:
        """
        确认是否使用自动配置

        Returns:
            bool: 是否使用自动配置
        """
        use_auto_config = input(
            f"\n{Fore.CYAN}是否使用此自动配置？(Y/n，默认: Y): {Style.RESET_ALL}"
        ).lower()
        return use_auto_config != "n"

    @staticmethod
    def select_response_column(response_cols: List[str]) -> str:
        """
        选择响应列（当有多个响应列时）

        Args:
            response_cols: 响应列列表

        Returns:
            str: 选择的响应列名
        """
        prompt_msg = "响应列"
        print_info(f"发现多个{prompt_msg}，请选择要使用的一个：")
        CLIInterface.print_column_table(response_cols)

        while True:
            try:
                choice = print_input_prompt(
                    f"请选择 {prompt_msg} (1-{len(response_cols)})"
                )
                index = int(choice) - 1
                if 0 <= index < len(response_cols):
                    selected_col = response_cols[index]
                    print_success(f"已选择列: {selected_col}")
                    return selected_col
                else:
                    print_error(f"无效的序号，请输入 1-{len(response_cols)}")
            except ValueError:
                print_error("请输入有效的数字")
            except KeyboardInterrupt:
                print_warning("\n操作已取消")
                sys.exit(0)

    @staticmethod
    def print_progress(current: int, total: int):
        """
        打印处理进度

        Args:
            current: 当前进度
            total: 总数
        """
        pending = total - current
        percentage = (current / total) * 100
        msg = f"正在处理: {current}/{total} ({percentage:.1f}%) | 待处理: {pending}"
        logger.info(msg)
        print(f"{Fore.BLUE}⏳ {msg}{Style.RESET_ALL}")

    @staticmethod
    def print_result_summary(total: int, processed: int, skipped: int, errors: int):
        """
        打印结果摘要

        Args:
            total: 总记录数
            processed: 成功处理数
            skipped: 跳过数
            errors: 错误数
        """
        print_summary_panel(total, processed, skipped, errors)

    @staticmethod
    def print_detailed_result_summary(
        total: int,
        processed: int,
        skipped: int,
        errors: int,
        file_path: str,
        output_path: str,
        provider_name: str,
        model_name: str,
    ):
        """
        打印详细结果摘要
        """
        from semantic_tester.ui.terminal_ui import print_detailed_summary_panel

        print_detailed_summary_panel(
            total,
            processed,
            skipped,
            errors,
            file_path,
            output_path,
            provider_name,
            model_name,
        )

    @staticmethod
    def print_comparison_result(
        doc_name: str, question: str, ai_answer: str, result: str, reason: str
    ):
        """
        打印单个比对结果

        Args:
            doc_name: 文档名称
            question: 问题
            ai_answer: AI回答
            result: 结果
            reason: 原因
        """
        print_comparison_result_panel(doc_name, question, ai_answer, result, reason)

    @staticmethod
    def print_error(message: str):
        """
        打印错误信息

        Args:
            message: 错误消息
        """
        print_error(message)

    @staticmethod
    def print_warning(message: str):
        """
        打印警告信息

        Args:
            message: 警告消息
        """
        print_warning(message)

    @staticmethod
    def print_success(message: str):
        """
        打印成功信息

        Args:
            message: 成功消息
        """
        print_success(message)

    @staticmethod
    def print_info(message: str):
        """
        打印信息

        Args:
            message: 信息内容
        """
        print_info(message)

    @staticmethod
    def get_confirmation(message: str, default: bool = True) -> bool:
        """
        获取用户确认

        Args:
            message: 确认消息
            default: 默认值

        Returns:
            bool: 用户确认结果
        """
        return confirm(message, default=default)
