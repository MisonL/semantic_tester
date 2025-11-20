"""
菜单处理器

提供交互式菜单功能。
"""

import logging
from typing import List

from colorama import Fore, Style

logger = logging.getLogger(__name__)


class MenuHandler:
    """菜单处理器"""

    @staticmethod
    def show_main_menu() -> str:
        """
        显示主菜单

        Returns:
            str: 用户选择
        """
        print(f"\n{Fore.CYAN}=== AI语义分析工具 ==={Style.RESET_ALL}")
        print("1. 开始新的语义分析")
        print("2. 查看使用说明")
        print("3. 配置设置")
        print("4. AI供应商管理")
        print("5. 退出程序")

        while True:
            choice = input(
                f"\n{Fore.YELLOW}请选择操作 (1-5): {Style.RESET_ALL}"
            ).strip()
            if choice in ["1", "2", "3", "4", "5"]:
                return choice
            print(f"{Fore.RED}无效选择，请输入 1-5{Style.RESET_ALL}")

    @staticmethod
    def show_config_menu() -> str:
        """
        显示配置菜单

        Returns:
            str: 用户选择
        """
        print(f"\n{Fore.CYAN}=== 配置设置 ==={Style.RESET_ALL}")
        print("1. 查看 API 密钥配置")
        print("2. 配置默认知识库目录")
        print("3. 配置默认输出目录")
        print("4. 重置配置")
        print("5. 返回主菜单")

        while True:
            choice = input(
                f"\n{Fore.YELLOW}请选择操作 (1-5): {Style.RESET_ALL}"
            ).strip()
            if choice in ["1", "2", "3", "4", "5"]:
                return choice
            print(f"{Fore.RED}无效选择，请输入 1-5{Style.RESET_ALL}")

    @staticmethod
    def show_provider_management_menu() -> str:
        """
        显示AI供应商管理菜单

        Returns:
            str: 用户选择
        """
        print(f"\n{Fore.CYAN}=== AI供应商管理 ==={Style.RESET_ALL}")
        print("1. 查看供应商验证状态")
        print("2. 切换当前供应商")
        print("3. 重新验证所有供应商")
        print("4. 查看供应商详细信息")
        print("5. 返回主菜单")

        while True:
            choice = input(
                f"\n{Fore.YELLOW}请选择操作 (1-5): {Style.RESET_ALL}"
            ).strip()
            if choice in ["1", "2", "3", "4", "5"]:
                return choice
            print(f"{Fore.RED}无效选择，请输入 1-5{Style.RESET_ALL}")

    @staticmethod
    def show_help_menu() -> str:
        """
        显示帮助菜单

        Returns:
            str: 用户选择
        """
        print(f"\n{Fore.CYAN}=== 使用说明 ==={Style.RESET_ALL}")
        print("1. 程序概述")
        print("2. Excel 文件格式说明")
        print("3. 知识库文档要求")
        print("4. 常见问题解答")
        print("5. 返回主菜单")

        while True:
            choice = input(
                f"\n{Fore.YELLOW}请选择查看内容 (1-5): {Style.RESET_ALL}"
            ).strip()
            if choice in ["1", "2", "3", "4", "5"]:
                return choice
            print(f"{Fore.RED}无效选择，请输入 1-5{Style.RESET_ALL}")

    @staticmethod
    def display_program_overview():
        """显示程序概述"""
        print(f"\n{Fore.GREEN}=== 程序概述 ==={Style.RESET_ALL}")
        print(
            """
本工具用于评估AI客服回答与源知识库文档内容的语义相符性。

主要功能：
• 使用 Google Gemini API 进行智能语义分析
• 支持批量处理 Excel 中的问答记录
• 自动检测 dify_chat_tester 输出格式
• 提供详细的判断依据和结果
• 支持增量保存，防止数据丢失

适用场景：
• AI 客服质量评估
• 知识库答案准确性检查
• 问答系统效果验证
        """
        )

    @staticmethod
    def display_excel_format_guide():
        """显示 Excel 文件格式说明"""
        print(f"\n{Fore.GREEN}=== Excel 文件格式说明 ==={Style.RESET_ALL}")
        print(
            """
标准格式要求：
必需列：
• 文档名称: 知识库文件名（如：产品手册.md）
• 问题点: 用户提问内容
• AI客服回答: AI生成的回答内容

输出列（自动添加）：
• 语义是否与源文档相符: "是"/"否"/错误状态
• 判断依据: 详细判断理由

Dify Chat Tester 格式支持：
• 自动检测包含"原始问题"/"用户输入"的列
• 自动识别以"响应"结尾的列
• 自动添加文档名称列
        """
        )

    @staticmethod
    def display_knowledge_base_guide():
        """显示知识库文档要求"""
        print(f"\n{Fore.GREEN}=== 知识库文档要求 ==={Style.RESET_ALL}")
        print(
            """
文档格式：
• 支持 Markdown (.md) 格式
• 文件编码：UTF-8
• 文件大小：建议小于 10MB

文档内容：
• 结构清晰，层次分明
• 信息准确，语言规范
• 覆盖常见问题和答案

目录结构：
• 可以是单个目录或嵌套目录
• 支持递归搜索所有 .md 文件
• 文档名称应与 Excel 中的"文档名称"列匹配
        """
        )

    @staticmethod
    def display_faq():
        """显示常见问题解答"""
        print(f"\n{Fore.GREEN}=== 常见问题解答 ==={Style.RESET_ALL}")
        print(
            """
Q: 如何获取 Google Gemini API 密钥？
A: 访问 https://aistudio.google.com/app/apikey 获取 API 密钥

Q: 支持多个 API 密钥吗？
A: 支持多个密钥轮换使用，避免速率限制

Q: 处理大量数据时程序中断怎么办？
A: 程序支持增量保存，重新运行会从中断处继续

Q: 语义分析的结果准确吗？
A: 基于 Gemini 2.5 Flash 模型，准确率较高，但仍需人工复核

Q: 如何提高分析效果？
A: 确保知识库文档内容完整、准确，问题表述清晰
        """
        )

    @staticmethod
    def select_from_list(
        title: str, options: List[str], allow_custom: bool = False
    ) -> str:
        """
        从列表中选择选项

        Args:
            title: 选择标题
            options: 选项列表
            allow_custom: 是否允许自定义输入

        Returns:
            str: 选择的选项
        """
        print(f"\n{Fore.CYAN}=== {title} ==={Style.RESET_ALL}")

        for i, option in enumerate(options, 1):
            print(f"{i}. {option}")

        if allow_custom:
            print(f"{len(options) + 1}. 自定义输入")

        while True:
            try:
                choice = input(
                    f"\n{Fore.YELLOW}请选择 (1-{len(options) + (1 if allow_custom else 0)}): {Style.RESET_ALL}"
                ).strip()
                choice_idx = int(choice) - 1

                if 0 <= choice_idx < len(options):
                    return options[choice_idx]
                elif allow_custom and choice_idx == len(options):
                    custom_input = input(
                        f"{Fore.YELLOW}请输入自定义值: {Style.RESET_ALL}"
                    ).strip()
                    if custom_input:
                        return custom_input
                    else:
                        print(f"{Fore.RED}自定义输入不能为空{Style.RESET_ALL}")
                else:
                    print(f"{Fore.RED}无效选择{Style.RESET_ALL}")
            except ValueError:
                print(f"{Fore.RED}请输入有效数字{Style.RESET_ALL}")

    @staticmethod
    def confirm_action(message: str) -> bool:
        """
        确认操作

        Args:
            message: 确认消息

        Returns:
            bool: 用户确认结果
        """
        while True:
            response = (
                input(f"\n{Fore.YELLOW}{message} (y/N): {Style.RESET_ALL}")
                .lower()
                .strip()
            )
            if response == "y":
                return True
            elif response in ["n", ""]:
                return False
            else:
                print(f"{Fore.RED}请输入 y 或 n{Style.RESET_ALL}")

    @staticmethod
    def get_input_with_validation(
        prompt: str, validator=None, error_message: str = "输入无效，请重试"
    ) -> str:
        """
        获取带验证的用户输入

        Args:
            prompt: 输入提示
            validator: 验证函数
            error_message: 错误消息

        Returns:
            str: 用户输入
        """
        while True:
            user_input = input(f"{Fore.YELLOW}{prompt}: {Style.RESET_ALL}").strip()
            if not user_input:
                continue

            if validator is None or validator(user_input):
                return user_input
            else:
                print(f"{Fore.RED}{error_message}{Style.RESET_ALL}")
