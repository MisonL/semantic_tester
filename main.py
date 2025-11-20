#!/usr/bin/env python3
"""
AI客服问答语义比对工具

主程序入口点 - 使用模块化架构
"""

import logging
import sys
from typing import Optional

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

        # 获取其他配置
        knowledge_base_dir = CLIInterface.get_knowledge_base_dir()
        show_comparison_result = CLIInterface.ask_show_comparison_result()
        default_output_path = self.config.get_default_output_path(excel_path)
        output_path = CLIInterface.get_output_path(default_output_path)

        # 确保输出目录存在
        self.config.ensure_output_dir(output_path)

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
        if not self.excel_processor:
            logger.error("Excel处理器未初始化")
            return

        total_records = self.excel_processor.get_total_records()
        logger.info(f"共需处理 {total_records} 条问答记录。")

        processed_count = 0
        skipped_count = 0
        error_count = 0

        # 单线程顺序处理
        if not self.excel_processor or self.excel_processor.df is None:
            logger.error("Excel数据未加载")
            return

        for row_index, (_, _) in enumerate(self.excel_processor.df.iterrows()):
            row_number = row_index + 1
            # pandas DataFrame的索引处理 - 使用row_index作为行号
            # 对于大多数用例，我们可以直接使用row_index作为实际的行索引
            index_int = row_index

            # 显示处理进度
            CLIInterface.print_progress(row_number, total_records)

            # 获取行数据
            row_data = self.excel_processor.get_row_data(row_index, column_mapping)

            # 验证行数据
            validation_errors = ValidationUtils.validate_row_data(row_data)
            if validation_errors:
                errors_str = "; ".join(validation_errors)
                error_msg = f"跳过第 {row_number}/{total_records} 条记录：{errors_str}"
                logger.warning(error_msg)
                self.excel_processor.save_result(
                    row_index=index_int,
                    result="跳过",
                    reason="; ".join(validation_errors),
                    result_columns=result_columns,
                )
                skipped_count += 1

                # 保存中间结果
                if row_number % self.config.auto_save_interval == 0:
                    self.excel_processor.save_intermediate_results(
                        output_path, row_number
                    )
                continue

            # 读取知识库文档内容
            doc_content = self._read_document_content(
                knowledge_base_dir=knowledge_base_dir, doc_name=row_data["doc_name"]
            )

            if not doc_content:
                logger.warning(
                    f"第 {row_number}/{total_records} 条记录：未找到对应的Markdown文件"
                )
                self.excel_processor.save_result(
                    row_index=index_int,
                    result="源文档未找到",
                    reason=f"未找到对应的Markdown文件：{row_data['doc_name']}",
                    result_columns=result_columns,
                )
                # 每处理完一条记录就保存结果（保持与原始代码一致）
                self.excel_processor.save_intermediate_results(output_path, row_number)
                error_count += 1
                continue

            # 调用语义比对 API
            try:
                # 优先使用新的供应商管理器，保持向后兼容
                if self.provider_manager:
                    result, reason = self.provider_manager.check_semantic_similarity(
                        question=row_data["question"],
                        ai_answer=row_data["ai_answer"],
                        source_document=doc_content,
                    )
                elif self.api_handler:
                    result, reason = check_semantic_similarity(
                        gemini_api_handler=self.api_handler,
                        question=row_data["question"],
                        ai_answer=row_data["ai_answer"],
                        source_document_content=doc_content,
                    )
                else:
                    logger.error("没有可用的 API 处理器")
                    result = "错误"
                    reason = "没有可用的 API 处理器"

                # 保存结果
                self.excel_processor.save_result(
                    row_index=index_int,
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

                if result not in ["错误", "跳过"]:
                    processed_count += 1
                else:
                    error_count += 1

            except Exception as e:
                logger.error(f"处理第 {row_number} 行时发生错误: {e}")
                self.excel_processor.save_result(
                    row_index=index_int,
                    result="错误",
                    reason=f"处理异常: {str(e)}",
                    result_columns=result_columns,
                )
                error_count += 1

            # 每处理完一条记录就保存结果（保持与原始代码一致）
            self.excel_processor.save_intermediate_results(output_path, row_number)

        # 保存最终结果
        self.excel_processor.save_final_results(output_path)

        # 显示处理摘要
        CLIInterface.print_result_summary(
            total=total_records,
            processed=processed_count,
            skipped=skipped_count,
            errors=error_count,
        )

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

        while True:
            # 使用简洁菜单显示
            LoggerUtils.print_simple_menu()

            try:
                choice = input("请输入选项 (1-5): ").strip()
            except (EOFError, KeyboardInterrupt):
                print("\n👋 感谢使用 AI语义分析工具！")
                break

            if choice == "1":
                # 开始新的语义分析
                self.run_interactive_mode()
            elif choice == "2":
                # 查看使用说明
                self._show_help_menu(MenuHandler())
            elif choice == "3":
                # 配置设置
                self._show_config_menu(MenuHandler())
            elif choice == "4":
                # AI供应商管理
                self._show_provider_management_menu(MenuHandler())
            elif choice == "5":
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

    def _show_config_menu(self, menu_handler):
        """显示配置菜单"""
        while True:
            choice = menu_handler.show_config_menu()

            if choice == "1":
                # 查看 API 密钥配置
                self.env_manager.print_env_status()
                print(f"API 密钥预览: {self.env_manager.get_api_keys_preview()}")
            elif choice == "2":
                # 配置默认知识库目录
                if self.config.update_from_user_input(
                    "default_knowledge_base_dir", "请输入默认知识库目录路径"
                ):
                    self.config.save_settings()
                    print("配置已保存")
            elif choice == "3":
                # 配置默认输出目录
                if self.config.update_from_user_input(
                    "default_output_dir", "请输入默认输出目录路径"
                ):
                    self.config.save_settings()
                    print("配置已保存")
            elif choice == "4":
                # 重置配置
                if menu_handler.confirm_action("确定要重置所有配置吗？"):
                    self.config.reset_to_defaults()
                    self.config.save_settings()
                    print("配置已重置")
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

        # 显示所有供应商
        providers = self.provider_manager.get_available_providers()

        if not providers:
            print("❌ 没有可用的供应商")
            input("\n按回车键继续...")
            return

        print("\n可用供应商:")
        for i, provider_info in enumerate(providers, 1):
            provider_name = provider_info["name"]
            is_configured = provider_info["configured"]
            is_current = provider_info.get("is_current", False)

            status = "✅ 已配置" if is_configured else "❌ 未配置"
            current_marker = " (当前)" if is_current else ""

            print(f"{i}. {provider_name}{current_marker} - {status}")

        # 获取用户选择
        while True:
            try:
                choice_input = input(
                    f"\n请选择要切换到的供应商 (1-{len(providers)}) 或按回车取消: "
                ).strip()

                if not choice_input:
                    print("操作已取消")
                    break

                choice_index = int(choice_input)
                if 1 <= choice_index <= len(providers):
                    selected_provider_info = providers[choice_index - 1]
                    selected_provider_id = selected_provider_info["id"]
                    selected_provider = self.provider_manager.get_provider(
                        selected_provider_id
                    )

                    if self.provider_manager.set_current_provider(selected_provider_id):
                        print(f"\n✅ 已切换到供应商: {selected_provider.name}")

                        # 验证新供应商的API密钥
                        if selected_provider.is_configured():
                            print("正在验证API密钥...")
                            is_valid = self.provider_manager._validate_provider_api_key(
                                selected_provider
                            )
                            if is_valid:
                                print("✅ API密钥验证通过")
                            else:
                                print("⚠️  API密钥验证失败，可能无法正常使用")
                        else:
                            print("⚠️  该供应商未配置，可能无法正常使用")

                        input("\n按回车键继续...")
                        break
                    else:
                        print("❌ 切换失败")
                else:
                    print(f"❌ 无效的选择，请输入 1-{len(providers)} 之间的数字")
            except ValueError:
                print("❌ 请输入有效的数字")
            except KeyboardInterrupt:
                print("\n操作已取消")
                break

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
            print(f"默认模型: {provider_info['default_model']}")
            print(f"可用模型数: {len(provider_info['models'])}")

            # 显示模型列表
            if provider_info["models"]:
                print(f"模型列表: {', '.join(provider_info['models'][:5])}")
                if len(provider_info["models"]) > 5:
                    print(f"          ... 共 {len(provider_info['models'])} 个模型")

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
        # 创建应用实例
        app = SemanticTestApp()

        # 初始化应用
        if not app.initialize():
            sys.exit(1)

        # 检查命令行参数
        if len(sys.argv) > 1:
            # 检查帮助参数
            if sys.argv[1] in ["-h", "--help", "help"]:
                print(help_text())
                sys.exit(0)

            # 命令行模式 - 直接处理指定文件
            if len(sys.argv) >= 2:
                excel_path = sys.argv[1]
                knowledge_base_dir = sys.argv[2] if len(sys.argv) > 2 else None

                # 验证文件路径
                if not ValidationUtils.is_valid_file_path(
                    excel_path, [".xlsx", ".xls"]
                ):
                    print(f"错误: 无效的 Excel 文件路径: {excel_path}")
                    sys.exit(1)

                # 设置 Excel 处理器
                app.excel_processor = ExcelProcessor(excel_path)

                if not app.excel_processor.load_excel():
                    print(f"错误: 无法加载 Excel 文件: {excel_path}")
                    sys.exit(1)

                # 如果没有提供知识库目录，询问用户
                if not knowledge_base_dir:
                    knowledge_base_dir = CLIInterface.get_knowledge_base_dir()

                # 使用默认配置进行快速处理
                print("\n" + "=" * 60)
                print("命令行快速处理模式")
                print("=" * 60)

                # 检测文件格式
                format_info = app.excel_processor.detect_format()
                app.excel_processor.display_format_info()

                # 自动适配 dify 格式
                if format_info["is_dify_format"]:
                    app.excel_processor.auto_add_document_column()

                # 获取列映射配置（自动配置）
                column_mapping = app.excel_processor.get_user_column_mapping(
                    auto_config=format_info["is_dify_format"]
                )

                # 获取结果列配置（使用默认值）
                result_columns = {
                    "similarity_result_col": ("语义是否与源文档相符", -1),
                    "reason_col": ("判断依据", -1),
                }

                # 设置结果列
                app.excel_processor.setup_result_columns(result_columns)

                # 获取输出路径
                default_output_path = app.config.get_default_output_path(excel_path)
                output_path = CLIInterface.get_output_path(default_output_path)

                # 确保输出目录存在
                app.config.ensure_output_dir(output_path)

                print(f"\n📊 开始处理 Excel 文件: {excel_path}")
                print(f"📚 知识库目录: {knowledge_base_dir}")
                print(f"💾 输出路径: {output_path}")
                print("=" * 60)

                # 开始处理
                app.process_data(
                    knowledge_base_dir=knowledge_base_dir,
                    column_mapping=column_mapping,
                    result_columns=result_columns,
                    output_path=output_path,
                    show_comparison_result=False,
                )

                print("\n" + "=" * 60)
                print("✅ 命令行快速处理完成！")
                print("=" * 60)
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


if __name__ == "__main__":
    main()
