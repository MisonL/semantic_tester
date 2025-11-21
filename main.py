#!/usr/bin/env python3
"""
AI客服问答语义比对工具

主程序入口点 - 使用模块化架构
"""

import logging
import sys
from typing import Optional
from colorama import Fore, Style

# 导入项目模块
from semantic_tester.api import GeminiAPIHandler, check_semantic_similarity
from semantic_tester.api.provider_manager import ProviderManager
from semantic_tester.excel import ExcelProcessor
from semantic_tester.ui import CLIInterface
from semantic_tester.config import EnvManager, Config
from semantic_tester.utils import FileUtils, LoggerUtils, ValidationUtils

# 设置日志 - 使用简洁模式
LoggerUtils.setup_logging(quiet_console=True)
logger = logging.getLogger(__name__)


class SemanticTestApp:
    """语义测试应用主类"""

    def __init__(self):
        """初始化应用"""
        self.env_manager = EnvManager()
        self.config = Config()
        self.api_handler: Optional[GeminiAPIHandler] = None  # 保持向后兼容
        self.provider_manager: Optional[ProviderManager] = None  # 新的多供应商管理器
        self.excel_processor: Optional[ExcelProcessor] = None

    def initialize(self) -> bool:
        """
        初始化应用程序

        Returns:
            bool: 初始化是否成功
        """
        # 显示简洁启动横幅
        LoggerUtils.print_startup_banner()

        # 记录系统信息到文件（不在控制台显示）
        LoggerUtils.log_system_info()
        LoggerUtils.log_package_info()

        # 静默初始化供应商管理器
        try:
            # 临时静默控制台输出，避免显示初始化过程的WARNING和CRITICAL消息
            LoggerUtils.silence_console_temporarily()
            self._initialize_provider_manager()
            LoggerUtils.restore_console_level()
        except Exception as e:
            LoggerUtils.restore_console_level()
            logger.error(f"初始化供应商管理器失败: {e}")
            return False

        # 保持向后兼容性：如果有 Gemini 密钥，初始化传统处理器
        if self.env_manager.gemini_api_keys:
            try:
                # 静默初始化传统处理器
                LoggerUtils.silence_console_temporarily()
                self.api_handler = GeminiAPIHandler(
                    api_keys=self.env_manager.gemini_api_keys,
                    model_name=self.env_manager.get_gemini_model(),
                    prompt_template="",  # semantic_tester 的提示词在 get_prompt 方法中构建
                )
                LoggerUtils.restore_console_level()
                logger.info("传统 Gemini API 处理器已初始化（向后兼容）")
            except Exception as e:
                LoggerUtils.restore_console_level()
                logger.error(f"初始化传统 Gemini API 处理器失败: {e}")

        # 显示供应商状态摘要
        if self.provider_manager:
            providers_info = {
                "total": len(self.provider_manager.providers),
                "configured": len(self.provider_manager.get_configured_providers()),
                "current": (
                    self.provider_manager.get_current_provider_name()
                    if self.provider_manager.get_current_provider()
                    else "无"
                ),
            }
            LoggerUtils.print_provider_summary(providers_info)

            # 如果没有配置的供应商，显示提示
            if not self.provider_manager.has_configured_providers():
                LoggerUtils.console_print(
                    "💡 提示: 暂无已配置的AI供应商，请配置 .env 文件或环境变量",
                    "WARNING",
                )

        return True

    def _initialize_provider_manager(self):
        """初始化供应商管理器"""
        # 构建供应商配置
        provider_config = {
            "ai_providers": self.env_manager.get_ai_providers(),
            "gemini_api_keys": self.env_manager.gemini_api_keys,
            "gemini_model": self.env_manager.get_gemini_model(),
            "openai": self.env_manager.get_openai_config(),
            "anthropic": self.env_manager.get_anthropic_config(),
            "dify": self.env_manager.get_dify_config(),
            "iflow": self.env_manager.get_iflow_config(),
            "batch": self.env_manager.get_batch_config(),
        }

        self.provider_manager = ProviderManager(provider_config)

        # 不再显示详细供应商状态，使用简洁摘要替代
        if not self.provider_manager:
            logger.error("供应商管理器初始化失败")

    def run_interactive_mode(self):
        """运行交互式模式"""
        CLIInterface.print_header()

        # 供应商选择和配置
        if self.provider_manager:
            # 如果没有已配置的供应商，提供配置选项
            if not self.provider_manager.has_configured_providers():
                print("\n⚠️  未检测到已配置的 AI 供应商")
                configure = input("是否现在配置 API 密钥? (y/N): ").strip().lower()
                if configure in ["y", "yes"]:
                    CLIInterface.configure_api_keys_interactive(self.env_manager)
                    # 重新初始化供应商管理器以加载新配置
                    self._initialize_provider_manager()

            # 选择供应商
            selected_provider_id = CLIInterface.select_ai_provider(
                self.provider_manager
            )
            if not selected_provider_id:
                print("❌ 未选择供应商，程序将退出")
                return

        # 获取 Excel 文件
        excel_path = CLIInterface.get_excel_file()
        self.excel_processor = ExcelProcessor(excel_path)

        # 加载 Excel 文件
        if not self.excel_processor.load_excel():
            logger.error("无法加载 Excel 文件")
            return

        # 检测文件格式
        format_info = self.excel_processor.detect_format()
        self.excel_processor.display_format_info()

        # 自动适配 dify 格式
        if format_info["is_dify_format"]:
            self.excel_processor.auto_add_document_column()

            # 处理多个响应列的情况
            response_cols = format_info["response_cols"]
            if len(response_cols) > 1:
                selected_response_col = CLIInterface.select_response_column(
                    response_cols
                )
                # 更新格式信息中的响应列
                format_info["response_cols"] = [selected_response_col]

            # 询问是否使用自动配置
            if CLIInterface.confirm_auto_config():
                column_mapping = self.excel_processor.get_user_column_mapping(
                    auto_config=True
                )
            else:
                column_mapping = self.excel_processor.get_user_column_mapping(
                    auto_config=False
                )
        else:
            column_mapping = self.excel_processor.get_user_column_mapping(
                auto_config=False
            )

        # 获取结果保存列配置
        result_columns = self.excel_processor.get_result_columns()
        self.excel_processor.setup_result_columns(result_columns)

        # 确认知识库目录
        print(f"\n{Fore.CYAN}=== 确认任务配置 ==={Style.RESET_ALL}")
        knowledge_base_dir = CLIInterface.get_knowledge_base_dir()
        print(f"✅ 知识库目录: {knowledge_base_dir}")

        # 确认输出目录
        default_output_path = self.config.get_default_output_path(excel_path)
        output_path = CLIInterface.get_output_path(default_output_path)
        print(f"✅ 输出目录: {output_path}")

        # 获取其他配置
        show_comparison_result = CLIInterface.ask_show_comparison_result()

        # 确保输出目录存在
        self.config.ensure_output_dir(output_path)

        # 最终确认
        from semantic_tester.ui.menu import MenuHandler
        if MenuHandler.confirm_action("确认开始处理吗？"):
            print(f"\n{Fore.GREEN}开始处理数据...{Style.RESET_ALL}")
        else:
            print("操作已取消")
            return

        # 开始处理
        self.process_data(
            knowledge_base_dir=knowledge_base_dir,
            column_mapping=column_mapping,
            result_columns=result_columns,
            output_path=output_path,
            show_comparison_result=show_comparison_result,
        )

    def process_data(
        self,
        knowledge_base_dir: str,
        column_mapping: dict,
        result_columns: dict,
        output_path: str,
        show_comparison_result: bool,
    ):
        """
        处理数据

        Args:
            knowledge_base_dir: 知识库目录
            column_mapping: 列映射配置
            result_columns: 结果列配置
            output_path: 输出路径
            show_comparison_result: 是否显示比对结果
        """
        excel_processor = self._get_excel_processor_or_error()
        if not excel_processor:
            return

        total_records = excel_processor.get_total_records()
        logger.info(f"共需处理 {total_records} 条问答记录。")

        processed_count = 0
        skipped_count = 0
        error_count = 0

        # 处理每一行数据
        for row_index in range(total_records):
            result = self._process_single_row(
                row_index=row_index,
                total_records=total_records,
                knowledge_base_dir=knowledge_base_dir,
                column_mapping=column_mapping,
                result_columns=result_columns,
                output_path=output_path,
                show_comparison_result=show_comparison_result,
                excel_processor=excel_processor,
            )

            if result == "processed":
                processed_count += 1
            elif result == "skipped":
                skipped_count += 1
            else:
                error_count += 1

        # 保存最终结果
        excel_processor.save_final_results(output_path)

        # 显示处理摘要
        CLIInterface.print_result_summary(
            total=total_records,
            processed=processed_count,
            skipped=skipped_count,
            errors=error_count,
        )

    def _validate_excel_processor(self) -> bool:
        """
        验证Excel处理器是否已正确初始化

        Returns:
            bool: 验证是否通过
        """
        if not self.excel_processor:
            logger.error("Excel处理器未初始化")
            return False

        if self.excel_processor.df is None:
            logger.error("Excel数据未加载")
            return False

        return True

    def _get_excel_processor_or_error(self) -> Optional["ExcelProcessor"]:
        """
        获取Excel处理器或返回None

        Returns:
            ExcelProcessor or None: Excel处理器实例
        """
        if not self._validate_excel_processor():
            return None
        return self.excel_processor

    def _process_single_row(
        self,
        row_index: int,
        total_records: int,
        knowledge_base_dir: str,
        column_mapping: dict,
        result_columns: dict,
        output_path: str,
        show_comparison_result: bool,
        excel_processor: "ExcelProcessor",
    ) -> str:
        """
        处理单行数据

        Args:
            row_index: 行索引
            total_records: 总记录数
            knowledge_base_dir: 知识库目录
            column_mapping: 列映射配置
            result_columns: 结果列配置
            output_path: 输出路径
            show_comparison_result: 是否显示比对结果

        Returns:
            str: 处理结果状态 ("processed", "skipped", "error")
        """
        row_number = row_index + 1

        # 显示处理进度
        CLIInterface.print_progress(row_number, total_records)

        # 获取行数据
        row_data = excel_processor.get_row_data(row_index, column_mapping)

        # 验证行数据
        validation_errors = ValidationUtils.validate_row_data(row_data)
        if validation_errors:
            self._handle_validation_errors(
                row_index, row_number, total_records, validation_errors,
                result_columns, output_path, excel_processor
            )
            return "skipped"

        # 读取知识库文档内容
        doc_content = self._read_document_content(
            knowledge_base_dir=knowledge_base_dir, doc_name=row_data["doc_name"]
        )

        if not doc_content:
            self._handle_missing_document(
                row_index, row_number, total_records, row_data["doc_name"],
                result_columns, output_path, excel_processor
            )
            return "error"

        # 调用语义比对 API
        try:
            result, reason = self._call_semantic_api(row_data, doc_content)

            # 保存结果
            excel_processor.save_result(
                row_index=row_index,
                result=result,
                reason=reason,
                result_columns=result_columns,
            )

            # 显示结果（如果启用）
            if show_comparison_result and result not in ["错误", "跳过"]:
                CLIInterface.print_comparison_result(
                    doc_name=row_data["doc_name"],
                    question=row_data["question"],
                    result=result,
                    reason=reason,
                )

            # 保存中间结果
            excel_processor.save_intermediate_results(output_path, row_number)

            return "processed" if result not in ["错误", "跳过"] else "error"

        except Exception as e:
            self._handle_processing_error(
                row_index, row_number, e, result_columns, output_path, excel_processor
            )
            return "error"

    def _handle_validation_errors(
        self,
        row_index: int,
        row_number: int,
        total_records: int,
        validation_errors: list,
        result_columns: dict,
        output_path: str,
        excel_processor: "ExcelProcessor",
    ):
        """
        处理验证错误
        """
        errors_str = "; ".join(validation_errors)
        error_msg = f"跳过第 {row_number}/{total_records} 条记录：{errors_str}"
        logger.warning(error_msg)
        excel_processor.save_result(
            row_index=row_index,
            result="跳过",
            reason=errors_str,
            result_columns=result_columns,
        )

        # 保存中间结果
        if row_number % self.config.auto_save_interval == 0:
            excel_processor.save_intermediate_results(output_path, row_number)

    def _handle_missing_document(
        self,
        row_index: int,
        row_number: int,
        total_records: int,
        doc_name: str,
        result_columns: dict,
        output_path: str,
        excel_processor: "ExcelProcessor",
    ):
        """
        处理文档缺失的情况
        """
        logger.warning(
            f"第 {row_number}/{total_records} 条记录：未找到对应的Markdown文件"
        )
        excel_processor.save_result(
            row_index=row_index,
            result="源文档未找到",
            reason=f"未找到对应的Markdown文件：{doc_name}",
            result_columns=result_columns,
        )
        # 每处理完一条记录就保存结果（保持与原始代码一致）
        excel_processor.save_intermediate_results(output_path, row_number)

    def _call_semantic_api(self, row_data: dict, doc_content: str) -> tuple[str, str]:
        """
        调用语义比对API

        Returns:
            tuple[str, str]: (结果, 原因)
        """
        # 优先使用新的供应商管理器，保持向后兼容
        if self.provider_manager:
            return self.provider_manager.check_semantic_similarity(
                question=row_data["question"],
                ai_answer=row_data["ai_answer"],
                source_document=doc_content,
            )
        elif self.api_handler:
            return check_semantic_similarity(
                gemini_api_handler=self.api_handler,
                question=row_data["question"],
                ai_answer=row_data["ai_answer"],
                source_document_content=doc_content,
            )
        else:
            logger.error("没有可用的 API 处理器")
            return "错误", "没有可用的 API 处理器"

    def _handle_processing_error(
        self,
        row_index: int,
        row_number: int,
        error: Exception,
        result_columns: dict,
        output_path: str,
        excel_processor: "ExcelProcessor",
    ):
        """
        处理处理过程中的错误
        """
        logger.error(f"处理第 {row_number} 行时发生错误: {error}")
        excel_processor.save_result(
            row_index=row_index,
            result="错误",
            reason=f"处理异常: {str(error)}",
            result_columns=result_columns,
        )
        # 每处理完一条记录就保存结果（保持与原始代码一致）
        excel_processor.save_intermediate_results(output_path, row_number)

    def _read_document_content(
        self, knowledge_base_dir: str, doc_name: str
    ) -> Optional[str]:
        """
        读取文档内容

        Args:
            knowledge_base_dir: 知识库目录
            doc_name: 文档名称

        Returns:
            Optional[str]: 文档内容，读取失败返回 None
        """
        # 确保文档名称有 .md 扩展名
        if not doc_name.lower().endswith(".md"):
            doc_name += ".md"

        # 查找文档文件（首先尝试直接路径，保持与原始代码一致）
        doc_path = FileUtils.find_file_by_name(
            knowledge_base_dir, doc_name, recursive=False
        )
        if not doc_path:
            logger.warning(f"未找到文档: {doc_name}")
            return None

        # 读取文档内容
        content = FileUtils.read_file_content(doc_path)
        if content is None:
            logger.error(f"无法读取文档内容: {doc_path}")
            return None

        logger.debug(f"成功读取文档: {doc_name} ({len(content)} 字符)")
        return content

    def run_menu_mode(self):
        """运行菜单模式"""
        from semantic_tester.ui.menu import MenuHandler

        menu_handler = MenuHandler()

        while True:
            try:
                # 使用菜单处理器获取用户选择
                choice = menu_handler.show_main_menu()
            except (EOFError, KeyboardInterrupt):
                print("\n👋 感谢使用 AI语义分析工具！")
                break

            if choice == "1":
                # 开始新的语义分析
                self.run_interactive_mode()
            elif choice == "2":
                # 查看使用说明
                self._show_help_menu(menu_handler)
            elif choice == "3":
                # AI供应商管理
                self._show_provider_management_menu(menu_handler)
            elif choice == "4":
                # 退出程序
                LoggerUtils.console_print("👋 感谢使用 AI语义分析工具！", "SUCCESS")
                break
            else:
                LoggerUtils.console_print("❌ 无效选项，请重新选择", "WARNING")

    def _show_help_menu(self, menu_handler):
        """显示帮助菜单"""
        while True:
            choice = menu_handler.show_help_menu()

            if choice == "1":
                menu_handler.display_program_overview()
            elif choice == "2":
                menu_handler.display_excel_format_guide()
            elif choice == "3":
                menu_handler.display_knowledge_base_guide()
            elif choice == "4":
                menu_handler.display_faq()
            elif choice == "5":
                break

    def _show_provider_management_menu(self, menu_handler):
        """显示AI供应商管理菜单"""
        while True:
            choice = menu_handler.show_provider_management_menu()

            if choice == "1":
                # 查看供应商验证状态
                self._show_provider_validation_status()
            elif choice == "2":
                # 切换当前供应商
                self._switch_current_provider()
            elif choice == "3":
                # 重新验证所有供应商
                self._revalidate_all_providers()
            elif choice == "4":
                # 查看供应商详细信息
                self._show_provider_details()
            elif choice == "5":
                break

    def _show_provider_validation_status(self):
        """显示供应商验证状态"""
        if not self.provider_manager:
            print("❌ 供应商管理器未初始化")
            return

        print("\n" + "=" * 60)
        print("AI供应商验证状态")
        print("=" * 60)

        validation_status = self.provider_manager.get_provider_validation_status()

        print(f"\n总供应商数: {validation_status['total']}")
        print(f"✅ 验证通过: {validation_status['valid']} 个")
        print(f"❌ 验证失败: {validation_status['invalid']} 个")
        print(f"⚠️  未配置: {validation_status['unconfigured']} 个")

        print("\n" + "-" * 60)
        print("详细状态:")
        print("-" * 60)

        for provider_id, result in validation_status["results"].items():
            status_icon = (
                "✅"
                if result["valid"]
                else "❌" if result["status"] == "验证失败" else "⚠️"
            )
            print(f"\n{status_icon} {result['name']}")
            print(f"   状态: {result['status']}")
            print(f"   说明: {result['message']}")

        print("\n" + "=" * 60)

        current_provider = self.provider_manager.get_current_provider()
        if current_provider:
            print(f"\n当前使用供应商: {current_provider.name}")
        else:
            print("\n⚠️  暂无当前供应商")

        input("\n按回车键继续...")

    def _switch_current_provider(self):
        """切换当前供应商"""
        if not self.provider_manager:
            print("❌ 供应商管理器未初始化")
            return

        print("\n" + "=" * 60)
        print("切换当前供应商")
        print("=" * 60)

        providers = self.provider_manager.get_available_providers()
        if not providers:
            print("❌ 没有可用的供应商")
            input("\n按回车键继续...")
            return

        # 显示可用供应商
        self._display_providers_list(providers)

        # 获取用户选择并处理
        selected_provider = self._get_provider_selection(providers)
        if selected_provider:
            self._complete_provider_switch(selected_provider)

    def _display_providers_list(self, providers: list):
        """
        显示供应商列表
        """
        print("\n可用供应商:")
        for i, provider_info in enumerate(providers, 1):
            provider_name = provider_info["name"]
            is_configured = provider_info["configured"]
            is_current = provider_info.get("is_current", False)

            status = "✅ 已配置" if is_configured else "❌ 未配置"
            current_marker = " (当前)" if is_current else ""

            print(f"{i}. {provider_name}{current_marker} - {status}")

    def _get_provider_manager_or_error(self) -> Optional["ProviderManager"]:
        """
        获取供应商管理器或返回None

        Returns:
            ProviderManager or None: 供应商管理器实例
        """
        if not self.provider_manager:
            logger.error("供应商管理器未初始化")
            return None
        return self.provider_manager

    def _get_provider_selection(self, providers: list):
        """
        获取用户选择的供应商

        Returns:
            Provider or None: 选择的供应商对象
        """
        provider_manager = self._get_provider_manager_or_error()
        if not provider_manager:
            return None

        while True:
            try:
                choice_input = input(
                    f"\n请选择要切换到的供应商 (1-{len(providers)}) 或按回车取消: "
                ).strip()

                if not choice_input:
                    print("操作已取消")
                    return None

                choice_index = int(choice_input)
                if 1 <= choice_index <= len(providers):
                    selected_provider_info = providers[choice_index - 1]
                    selected_provider_id = selected_provider_info["id"]
                    return provider_manager.get_provider(selected_provider_id)
                else:
                    print(f"❌ 无效的选择，请输入 1-{len(providers)} 之间的数字")
            except ValueError:
                print("❌ 请输入有效的数字")
            except KeyboardInterrupt:
                print("\n操作已取消")
                return None

    def _complete_provider_switch(self, selected_provider):
        """
        完成供应商切换过程

        Args:
            selected_provider: 要切换到的供应商
        """
        provider_manager = self._get_provider_manager_or_error()
        if not provider_manager:
            return

        if provider_manager.set_current_provider(selected_provider.id):
            print(f"\n✅ 已切换到供应商: {selected_provider.name}")

            # 验证新供应商的API密钥
            self._validate_and_show_provider_status(selected_provider)

            input("\n按回车键继续...")
        else:
            print("❌ 切换失败")

    def _validate_and_show_provider_status(self, provider):
        """
        验证供应商并显示状态

        Args:
            provider: 要验证的供应商
        """
        provider_manager = self._get_provider_manager_or_error()
        if not provider_manager:
            return

        if provider.is_configured():
            print("正在验证API密钥...")
            is_valid = provider_manager._validate_provider_api_key(provider)
            if is_valid:
                print("✅ API密钥验证通过")
            else:
                print("⚠️  API密钥验证失败，可能无法正常使用")
        else:
            print("⚠️  该供应商未配置，可能无法正常使用")

    def _revalidate_all_providers(self):
        """重新验证所有供应商"""
        if not self.provider_manager:
            print("❌ 供应商管理器未初始化")
            return

        print("\n" + "=" * 60)
        print("重新验证所有供应商API密钥")
        print("=" * 60)
        print("\n正在验证，请稍候...")

        self.provider_manager.revalidate_all_providers()

        print("\n✅ 验证完成")
        input("\n按回车键查看验证结果...")

        # 显示验证结果
        self._show_provider_validation_status()

    def _show_provider_details(self):
        """显示供应商详细信息"""
        if not self.provider_manager:
            print("❌ 供应商管理器未初始化")
            return

        print("\n" + "=" * 60)
        print("AI供应商详细信息")
        print("=" * 60)

        providers = self.provider_manager.get_available_providers()

        if not providers:
            print("❌ 没有可用的供应商")
            input("\n按回车键继续...")
            return

        for provider_info in providers:
            print("\n" + "-" * 60)
            print(f"供应商: {provider_info['name']}")
            print("-" * 60)
            print(f"ID: {provider_info['id']}")
            print(f"配置状态: {'已配置' if provider_info['configured'] else '未配置'}")
            print(
                f"当前使用: {'是' if provider_info.get('is_current', False) else '否'}"
            )
            print(f"默认模型: {provider_info.get('default_model', 'N/A')}")
            print(f"可用模型数: {len(provider_info.get('models', []))}")

            # 显示模型列表
            models = provider_info.get('models', [])
            if models:
                print(f"模型列表: {', '.join(models[:5])}")
                if len(models) > 5:
                    print(f"          ... 共 {len(models)} 个模型")

        print("\n" + "=" * 60)
        input("\n按回车键继续...")


def help_text() -> str:
    """返回帮助文本"""
    return """
AI客服问答语义比对工具 - 使用说明

用法:
    python main.py [Excel文件路径] [知识库目录]
    python main.py --help

参数:
    Excel文件路径    要处理的Excel文件路径 (.xlsx 或 .xls)
    知识库目录      知识库文档目录路径 (可选，未提供时将询问用户)

选项:
    -h, --help     显示此帮助信息

示例:
    python main.py data.xlsx ./knowledge_base
    python main.py test.xlsx

功能:
    - 支持多种AI供应商 (Gemini, OpenAI, Dify)
    - 自动语义相似度分析
    - 增量保存处理结果
    - 优雅启动，无API密钥也可查看程序状态

配置:
    - 配置文件: 复制 .env.config.example 为 .env
    - 至少配置一个AI供应商的API密钥即可使用

快速配置:
    cp .env.config.example .env
    # 修改 .env 文件中的API密钥
    uv run python main.py
"""


def main():
    """主函数"""
    try:
        # 创建并初始化应用实例
        app = _create_and_initialize_app()
        if not app:
            sys.exit(1)

        # 检查命令行参数
        if len(sys.argv) > 1:
            # 处理命令行参数
            if _handle_help_argument():
                sys.exit(0)

            # 命令行模式处理
            _run_command_line_mode(app)
        else:
            # 交互式菜单模式
            app.run_menu_mode()

    except KeyboardInterrupt:
        print("\n\n程序被用户中断")
        sys.exit(0)
    except Exception as e:
        logger.error(f"程序运行时发生未捕获的异常: {e}", exc_info=True)
        print(f"程序运行出错: {e}")
        sys.exit(1)


def _create_and_initialize_app() -> Optional[SemanticTestApp]:
    """
    创建并初始化应用实例

    Returns:
        SemanticTestApp or None: 初始化成功返回应用实例，失败返回None
    """
    app = SemanticTestApp()
    if not app.initialize():
        return None
    return app


def _handle_help_argument() -> bool:
    """
    处理帮助参数

    Returns:
        bool: 如果是帮助参数返回True
    """
    if sys.argv[1] in ["-h", "--help", "help"]:
        print(help_text())
        return True
    return False


def _run_command_line_mode(app: SemanticTestApp):
    """
    运行命令行模式

    Args:
        app: 应用实例
    """
    if len(sys.argv) < 2:
        return

    excel_path = sys.argv[1]
    knowledge_base_dir = sys.argv[2] if len(sys.argv) > 2 else None

    # 验证并加载Excel文件
    if not _validate_and_load_excel(app, excel_path):
        sys.exit(1)

    # 确保excel_processor存在
    if not app.excel_processor:
        print("错误: Excel处理器未初始化")
        sys.exit(1)

    # 获取知识库目录
    if not knowledge_base_dir:
        knowledge_base_dir = CLIInterface.get_knowledge_base_dir()

    # 显示命令行模式信息
    _display_command_line_mode_header()

    # 检测并处理文件格式
    format_info = _detect_and_handle_file_format(app)

    # 获取列映射配置
    column_mapping = app.excel_processor.get_user_column_mapping(
        auto_config=format_info["is_dify_format"]
    )

    # 设置结果列和输出路径
    result_columns = _setup_result_columns(app)
    output_path = _get_output_path(app, excel_path)

    # 显示处理信息
    _display_processing_info(excel_path, knowledge_base_dir, output_path)

    # 开始处理
    app.process_data(
        knowledge_base_dir=knowledge_base_dir,
        column_mapping=column_mapping,
        result_columns=result_columns,
        output_path=output_path,
        show_comparison_result=False,
    )

    # 显示完成信息
    _display_completion_message()


def _validate_and_load_excel(app: SemanticTestApp, excel_path: str) -> bool:
    """
    验证并加载Excel文件

    Returns:
        bool: 成功返回True
    """
    """
    Returns:
        bool: 成功返回True
    """
    if not ValidationUtils.is_valid_file_path(excel_path, [".xlsx", ".xls"]):
        print(f"错误: 无效的 Excel 文件路径: {excel_path}")
        return False

    # 设置 Excel 处理器
    app.excel_processor = ExcelProcessor(excel_path)

    if not app.excel_processor.load_excel():
        print(f"错误: 无法加载 Excel 文件: {excel_path}")
        return False

    return True


def _display_command_line_mode_header():
    """显示命令行模式标题"""
    print("\n" + "=" * 60)
    print("命令行快速处理模式")
    print("=" * 60)


def _detect_and_handle_file_format(app: SemanticTestApp) -> dict:
    """
    检测并处理文件格式

    Returns:
        dict: 格式信息
    """
    if not app.excel_processor:
        print("错误: Excel处理器未初始化")
        return {"is_dify_format": False}

    format_info = app.excel_processor.detect_format()
    app.excel_processor.display_format_info()

    # 自动适配 dify 格式
    if format_info["is_dify_format"]:
        app.excel_processor.auto_add_document_column()

    return format_info


def _setup_result_columns(app: SemanticTestApp) -> dict:
    """
    设置结果列

    Returns:
        dict: 结果列配置
    """
    result_columns = {
        "similarity_result_col": ("语义是否与源文档相符", -1),
        "reason_col": ("判断依据", -1),
    }

    # 设置结果列
    if app.excel_processor:
        app.excel_processor.setup_result_columns(result_columns)

    return result_columns


def _get_output_path(app: SemanticTestApp, excel_path: str) -> str:
    """
    获取输出路径

    Returns:
        str: 输出路径
    """
    default_output_path = app.config.get_default_output_path(excel_path)
    output_path = CLIInterface.get_output_path(default_output_path)

    # 确保输出目录存在
    app.config.ensure_output_dir(output_path)

    return output_path


def _display_processing_info(
    excel_path: str, knowledge_base_dir: str, output_path: str
):
    """显示处理信息"""
    print(f"\n📊 开始处理 Excel 文件: {excel_path}")
    print(f"📚 知识库目录: {knowledge_base_dir}")
    print(f"💾 输出路径: {output_path}")
    print("=" * 60)


def _display_completion_message():
    """显示完成信息"""
    print("\n" + "=" * 60)
    print("✅ 命令行快速处理完成！")
    print("=" * 60)


if __name__ == "__main__":
    main()
