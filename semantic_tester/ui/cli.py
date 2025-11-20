"""
命令行界面处理

提供命令行交互功能。
"""

import logging
import os
import sys
from typing import List, Optional

from colorama import Fore, Style

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
            print("❌ 没有可用的 AI 供应商")
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
        显示供应商列表
        """
        print("\n=== AI 供应商选择 ===")
        print(
            f"可用供应商: {len(providers)} 个，已配置: {len(configured_providers)} 个"
        )

        # 显示供应商列表
        for i, provider_info in enumerate(providers, 1):
            # provider_id = provider_info["id"]  # 未使用，暂时注释
            provider_name = provider_info["name"]
            is_configured = provider_info["configured"]
            is_current = provider_info.get("is_current", False)

            status = "✅ 已配置" if is_configured else "❌ 未配置"
            current_marker = " (当前)" if is_current else ""

            print(f"{i}. {provider_name}{current_marker} - {status}")

    @staticmethod
    def _confirm_unconfigured_selection() -> bool:
        """
        确认是否选择未配置的供应商

        Returns:
            bool: True 表示继续，False 表示取消
        """
        print("\n⚠️  警告: 没有已配置的 AI 供应商")
        proceed = input("是否继续选择未配置的供应商? (y/N): ").strip().lower()
        return proceed in ["y", "yes"]

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
                choice_input = input(
                    "\n请选择供应商 (1-{}) 或按回车使用当前供应商: ".format(len(providers))
                ).strip()

                # 如果用户按回车，使用当前供应商
                if not choice_input:
                    return CLIInterface._use_current_provider(provider_manager)

                choice_index = int(choice_input)
                if 1 <= choice_index <= len(providers):
                    selected_provider_id = choices[choice_index - 1]
                    selected_provider = provider_manager.get_provider(
                        selected_provider_id
                    )

                    if not selected_provider.is_configured():
                        if not CLIInterface._confirm_unconfigured_provider(selected_provider):
                            continue

                    # 设置为当前供应商
                    provider_manager.set_current_provider(selected_provider_id)
                    print(f"✅ 已选择供应商: {selected_provider.name}")
                    return selected_provider_id
                else:
                    print(f"❌ 无效的选择，请输入 1-{len(providers)} 之间的数字")
            except ValueError:
                print("❌ 请输入有效的数字")
            except KeyboardInterrupt:
                print("\n操作已取消")
                return None

    @staticmethod
    def _use_current_provider(provider_manager):
        """
        使用当前供应商

        Returns:
            str: 当前供应商 ID 或 None
        """
        current_provider = provider_manager.get_current_provider()
        if current_provider:
            print(f"使用当前供应商: {current_provider.name}")
            return provider_manager.current_provider_id
        else:
            print("❌ 没有当前供应商")
            return None

    @staticmethod
    def _confirm_unconfigured_provider(provider) -> bool:
        """
        确认选择未配置的供应商

        Returns:
            bool: True 表示确认，False 表示取消
        """
        print(
            f"⚠️  供应商 {provider.name} 未配置，可能无法正常使用"
        )
        confirm = input("确认选择此供应商? (y/N): ").strip().lower()
        return confirm in ["y", "yes"]

    @staticmethod
    def show_provider_status(provider_manager):
        """
        显示供应商状态

        Args:
            provider_manager: 供应商管理器实例
        """
        if not provider_manager:
            print("❌ 供应商管理器未初始化")
            return

        provider_manager.print_provider_status()

    @staticmethod
    def configure_api_keys_interactive(env_manager):
        """
        交互式配置 API 密钥

        Args:
            env_manager: 环境管理器实例
        """
        print("\n=== API 密钥配置 ===")
        print("选择要配置的 AI 供应商:")

        choices = ["1. Gemini", "2. OpenAI", "3. Dify", "4. 返回上级菜单"]

        for choice in choices:
            print(choice)

        while True:
            try:
                selection = input("请选择 (1-4): ").strip()

                if selection == "1":
                    CLIInterface._configure_gemini_keys(env_manager)
                elif selection == "2":
                    CLIInterface._configure_openai_keys(env_manager)
                elif selection == "3":
                    CLIInterface._configure_dify_keys(env_manager)
                elif selection == "4":
                    break
                else:
                    print("❌ 无效选择，请输入 1-4")
            except KeyboardInterrupt:
                print("\n操作已取消")
                break

    @staticmethod
    def _configure_gemini_keys(env_manager):
        """配置 Gemini API 密钥"""
        print("\n--- Gemini API 密钥配置 ---")
        print("获取 API 密钥: https://aistudio.google.com/app/apikey")

        keys_input = input("请输入 Gemini API 密钥 (多个密钥用逗号分隔): ").strip()
        if keys_input:
            # 设置环境变量
            import os

            os.environ["GEMINI_API_KEY"] = keys_input
            print("✅ Gemini API 密钥已设置（当前会话有效）")
            print("💡 提示: 要永久保存，请在 .env 文件中配置或设置系统环境变量")

    @staticmethod
    def _configure_openai_keys(env_manager):
        """配置 OpenAI API 密钥"""
        print("\n--- OpenAI API 密钥配置 ---")
        print("获取 API 密钥: https://platform.openai.com/api-keys")

        api_key = input("请输入 OpenAI API 密钥: ").strip()
        if api_key:
            import os

            os.environ["OPENAI_API_KEY"] = api_key
            print("✅ OpenAI API 密钥已设置（当前会话有效）")
            print("💡 提示: 要永久保存，请在 .env 文件中配置或设置系统环境变量")

    @staticmethod
    def _configure_dify_keys(env_manager):
        """配置 Dify API 密钥"""
        print("\n--- Dify API 密钥配置 ---")
        print("获取 API 密钥: 从 Dify 工作台获取")

        api_key = input("请输入 Dify API 密钥: ").strip()
        if api_key:
            import os

            os.environ["DIFY_API_KEY"] = api_key
            print("✅ Dify API 密钥已设置（当前会话有效）")
            print("💡 提示: 要永久保存，请在 .env 文件中配置或设置系统环境变量")

    @staticmethod
    def get_excel_file() -> str:
        """
        获取用户输入的 Excel 文件路径

        Returns:
            str: Excel 文件路径
        """
        excel_files = CLIInterface._get_local_excel_files()

        while True:
            # 获取用户输入的文件路径
            excel_path = CLIInterface._get_user_file_input(excel_files)
            if excel_path is None:
                continue

            # 验证文件存在性
            if not CLIInterface._validate_file_exists(excel_path):
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
            CLIInterface._display_excel_files(excel_files)
            file_input = input("请输入 Excel 文件序号或直接输入文件路径: ")
            return CLIInterface._parse_file_input(file_input, excel_files)
        else:
            return input(
                "当前目录下没有找到 Excel 文件。请输入包含问答内容的 Excel 文件路径: "
            )

    @staticmethod
    def _display_excel_files(excel_files: list):
        """
        显示Excel文件列表
        """
        print("\n当前目录下的 Excel 文件:")
        for i, file_name in enumerate(excel_files):
            print(f"{i + 1}. {file_name}")

    @staticmethod
    def _parse_file_input(file_input: str, excel_files: list) -> Optional[str]:
        """
        解析用户输入的文件选择

        Args:
            file_input: 用户输入
            excel_files: Excel文件列表

        Returns:
            str: 文件路径
        """
        try:
            file_index = int(file_input)
            if 1 <= file_index <= len(excel_files):
                return excel_files[file_index - 1]
            else:
                print(
                    f"错误: 无效的文件序号 '{file_index}'。请重新输入。",
                    file=sys.stderr,
                )
                return None
        except ValueError:  # 用户输入的是路径
            return file_input

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
            print(
                f"错误: 文件 '{excel_path}' 不存在。请重新输入。", file=sys.stderr
            )
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
        while True:
            knowledge_base_dir = input(
                "请输入知识库文档目录路径 (例如: '处理后/' 或 '/path/to/knowledge_base/'): "
            )
            if not knowledge_base_dir:
                print("错误: 知识库文档目录路径不能为空。", file=sys.stderr)
                continue
            if not os.path.isdir(knowledge_base_dir):
                print(
                    f"错误: 目录 '{knowledge_base_dir}' 不存在。请重新输入。",
                    file=sys.stderr,
                )
                continue
            return knowledge_base_dir

    @staticmethod
    def get_output_path(default_path: str) -> str:
        """
        获取输出文件路径

        Args:
            default_path: 默认输出路径

        Returns:
            str: 输出文件路径
        """
        return (
            input(f"请输入结果Excel文件的保存路径 (默认: {default_path}): ")
            or default_path
        )

    @staticmethod
    def ask_show_comparison_result() -> bool:
        """
        询问是否在控制台显示比对结果

        Returns:
            bool: 是否显示比对结果
        """
        display_result_choice = input(
            "是否在控制台显示每个问题的比对结果？ (y/N，默认: N): "
        ).lower()
        return display_result_choice == "y"

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
        print(f"\n{Fore.YELLOW}发现多个响应列，请选择要使用的一个：{Style.RESET_ALL}")
        for i, col in enumerate(response_cols):
            print(f"  {i + 1}. {col}")

        while True:
            choice = input(f"请输入选择 (1-{len(response_cols)}, 默认: 1): ").strip()
            if not choice:
                choice = "1"

            try:
                choice_idx = int(choice) - 1
                if 0 <= choice_idx < len(response_cols):
                    return response_cols[choice_idx]
                else:
                    print(f"选择无效，请输入 1-{len(response_cols)} 之间的数字。")
            except ValueError:
                print("请输入有效的数字。")

    @staticmethod
    def print_progress(current: int, total: int):
        """
        打印处理进度

        Args:
            current: 当前进度
            total: 总数
        """
        logger.info(f"正在处理第 {current}/{total} 条记录...")

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
        print(f"\n{Fore.GREEN}=== 处理完成 ==={Style.RESET_ALL}")
        print(f"总记录数: {total}")
        print(f"成功处理: {processed}")
        print(f"跳过记录: {skipped}")
        print(f"错误记录: {errors}")

    @staticmethod
    def print_comparison_result(doc_name: str, question: str, result: str, reason: str):
        """
        打印单个比对结果

        Args:
            doc_name: 文档名称
            question: 问题
            result: 结果
            reason: 原因
        """
        print(f"\n{Fore.CYAN}📄 文档: {doc_name}{Style.RESET_ALL}")
        print(f"❓ 问题: {question[:100]}{'...' if len(question) > 100 else ''}")

        if result == "是":
            colored_result = f"{Fore.GREEN}✅ {result}{Style.RESET_ALL}"
        elif result == "否":
            colored_result = f"{Fore.RED}❌ {result}{Style.RESET_ALL}"
        else:
            colored_result = f"{Fore.YELLOW}⚠️ {result}{Style.RESET_ALL}"

        print(f"🔍 结果: {colored_result}")
        print(f"📝 原因: {reason[:150]}{'...' if len(reason) > 150 else ''}")

    @staticmethod
    def print_error(message: str):
        """
        打印错误信息

        Args:
            message: 错误消息
        """
        print(f"{Fore.RED}错误: {message}{Style.RESET_ALL}", file=sys.stderr)

    @staticmethod
    def print_warning(message: str):
        """
        打印警告信息

        Args:
            message: 警告消息
        """
        print(f"{Fore.YELLOW}警告: {message}{Style.RESET_ALL}")

    @staticmethod
    def print_success(message: str):
        """
        打印成功信息

        Args:
            message: 成功消息
        """
        print(f"{Fore.GREEN}✅ {message}{Style.RESET_ALL}")

    @staticmethod
    def print_info(message: str):
        """
        打印信息

        Args:
            message: 信息内容
        """
        print(f"ℹ️  {message}")

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
        suffix = " (Y/n): " if default else " (y/N): "
        response = input(message + suffix).lower().strip()

        if not response:
            return default

        return response == "y" if default else response != "n"
