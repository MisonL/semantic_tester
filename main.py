#!/usr/bin/env python3
"""
AI客服问答语义比对工具

主程序入口点 - 使用模块化架构

作者：Mison
邮箱：1360962086@qq.com
仓库：https://github.com/MisonL/semantic_tester
许可证：MIT

🔗 完美集成 Dify Chat Tester，支持直接读取其输出进行语义评估
"""

import logging
import os
import sys
from typing import Optional, TYPE_CHECKING
from colorama import Fore, Style

# 导入版本信息
from semantic_tester import __version__, __author__, __email__, __license__

# 延迟导入优化：只导入最基本的模块
from semantic_tester.config import EnvManager, Config
from semantic_tester.utils import LoggerUtils

if TYPE_CHECKING:
    from semantic_tester.api import check_semantic_similarity  # noqa: F401
    from semantic_tester.api.provider_manager import ProviderManager  # noqa: F401
    from semantic_tester.excel import ExcelProcessor  # noqa: F401
    from semantic_tester.ui import CLIInterface  # noqa: F401
    from semantic_tester.utils import FileUtils, ValidationUtils  # noqa: F401

# 设置日志 - 使用简洁模式
LoggerUtils.setup_logging(quiet_console=True)
logger = logging.getLogger(__name__)


class SemanticTestApp:
    """语义测试应用主类"""

    def __init__(self):
        """初始化应用"""
        self.env_manager = EnvManager()
        self.config = Config()
        self.api_handler: Optional["GeminiAPIHandler"] = None  # 保持向后兼容
        self.provider_manager: Optional["ProviderManager"] = None  # 新的多供应商管理器
        self.excel_processor: Optional["ExcelProcessor"] = None

    def initialize(self) -> bool:
        """
        初始化应用程序

        Returns:
            bool: 初始化是否成功
        """

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
            print()  # 添加空行，避免与前面内容同行
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
        # 延迟导入以加快启动速度
        from semantic_tester.api.provider_manager import ProviderManager  # noqa: F811

        # 直接传递EnvManager实例
        self.provider_manager = ProviderManager(self.env_manager)

        # 不再显示详细供应商状态，使用简洁摘要替代
        if not self.provider_manager:
            logger.error("供应商管理器初始化失败")

    def run_interactive_mode(self):  # noqa: C901
        """运行交互式模式"""
        # 延迟导入所需模块（实际运行时才加载）
        from semantic_tester.ui import CLIInterface  # noqa: F811
        from semantic_tester.excel import ExcelProcessor  # noqa: F811

        CLIInterface.print_header()

        # 供应商选择和配置
        if self.provider_manager:
            # 如果没有已配置的供应商，提供配置选项
            if not self.provider_manager.has_configured_providers():
                print("\n⚠️  未检测到已配置的 AI 供应商")
                configure = input("是否现在配置 API 密钥? (y/N，默认: N): ").strip().lower()
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
        use_auto_config = False
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

            # 询问是否使用自动配置 (只确认一次)
            print(f"\n{Fore.CYAN}自动配置将包含：{Style.RESET_ALL}")
            print("  • 列映射: 文档名称、问题点、AI客服回答")
            print("  • 结果列: 语义是否与源文档相符、判断依据")
            print("  • 缺失的列将自动添加")

            if CLIInterface.confirm_auto_config():
                # 自动配置模式：一次性完成所有配置
                use_auto_config = True
                column_mapping = self.excel_processor.get_user_column_mapping(
                    auto_config=True
                )
                # 不再显示列映射确认，已在display_format_info中显示过
            else:
                # 手动配置
                column_mapping = self.excel_processor.get_user_column_mapping(
                    auto_config=False
                )
        else:
            column_mapping = self.excel_processor.get_user_column_mapping(
                auto_config=False
            )

        # 获取结果保存列配置 (如果是自动配置模式，静默添加)
        result_columns = self.excel_processor.get_result_columns(
            auto_config=use_auto_config
        )
        if use_auto_config:
            print(
                f"\n{Fore.GREEN}✅ 已自动添加结果列: 语义是否与源文档相符、判断依据{Style.RESET_ALL}"
            )
        self.excel_processor.setup_result_columns(result_columns)

        # 智能建议文档名称填充
        self.excel_processor.suggest_document_names(auto_config=use_auto_config)

        # 确认知识库目录
        print(f"\n{Fore.CYAN}=== 确认任务配置 ==={Style.RESET_ALL}")
        knowledge_base_dir = CLIInterface.get_knowledge_base_dir()
        print(f"✅ 知识库目录: {knowledge_base_dir}")

        # 确认输出目录
        default_output_path = self.config.get_default_output_path(excel_path)
        output_path = CLIInterface.get_output_path(default_output_path)
        print(f"✅ 输出目录: {output_path}")

        # 获取其他配置
        if use_auto_config:
            show_comparison_result = True
            # print(f"✅ 默认显示比对结果") # 保持界面简洁，不打印多余信息
        else:
            show_comparison_result = CLIInterface.ask_show_comparison_result()

        # 确保输出目录存在
        self.config.ensure_output_dir(output_path)

        # 最终确认
        from semantic_tester.ui.menu import MenuHandler

        # 询问是否启用全量文档匹配
        print(f"\n{Fore.CYAN}⚙️  匹配模式设置{Style.RESET_ALL}")
        print("全量文档匹配模式将忽略 Excel 中的'文档名称'列，直接使用知识库中的所有文档进行比对。")
        
        # 从环境变量获取默认值
        # default_full_match = self.env_manager.get_use_full_doc_match()
        use_full_doc_match = MenuHandler.confirm_action("是否启用全量文档匹配？", default=False)
        
        if use_full_doc_match:
            print(f"{Fore.GREEN}✅ 已启用全量文档匹配{Style.RESET_ALL}")
        else:
            print(f"{Fore.YELLOW}📋 使用指定文档匹配模式{Style.RESET_ALL}")

        # 询问是否启用流式输出
        print(f"\n{Fore.CYAN}⚙️  流式输出设置{Style.RESET_ALL}")
        print("流式输出可以实时显示 AI 的思考过程，让您了解评估进展。")
        enable_stream = MenuHandler.confirm_action("是否启用流式输出？", default=True)
        
        if enable_stream:
            print(f"{Fore.GREEN}✅ 已启用流式输出{Style.RESET_ALL}")
        else:
            print(f"{Fore.YELLOW}📋 使用标准输出模式{Style.RESET_ALL}")

        # 如果是自动配置模式，跳过最终确认
        if use_auto_config:
            print(f"\n{Fore.GREEN}🚀 自动配置就绪，开始处理数据...{Style.RESET_ALL}")
        else:
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
            enable_stream=enable_stream,
            use_full_doc_match=use_full_doc_match,
        )

    def process_data(
        self,
        knowledge_base_dir: str,
        column_mapping: dict,
        result_columns: dict,
        output_path: str,
        show_comparison_result: bool,
        enable_stream: bool = False,
        use_full_doc_match: bool = False,
    ):
        """处理数据
        
        Args:
            knowledge_base_dir: 知识库目录
            column_mapping: 列映射配置
            result_columns: 结果列配置
            output_path: 输出路径
            show_comparison_result: 是否显示比对结果
            enable_stream: 是否启用流式输出
        """
        # 保存流式输出 / 思维链配置
        self.enable_stream = enable_stream
        # 思维链默认由环境变量 ENABLE_THINKING 控制（默认开启）
        try:
            self.enable_thinking = self.env_manager.get_enable_thinking()
        except AttributeError:
            # 向后兼容：如果 EnvManager 暂未实现该方法，则默认开启
            self.enable_thinking = True
        # 延迟导入
        from semantic_tester.ui import CLIInterface
        
        excel_processor = self._get_excel_processor_or_error()
        if not excel_processor:
            return

        total_records = excel_processor.get_total_records()
        
        # 尝试加载现有结果以恢复进度
        loaded_count = 0
        if os.path.exists(output_path):
            print(f"\n{Fore.CYAN}检测到现有输出文件，正在检查进度...{Style.RESET_ALL}")
            loaded_count = excel_processor.load_existing_results(output_path, result_columns)
            if loaded_count > 0:
                print(f"{Fore.GREEN}已恢复 {loaded_count} 条历史记录，将跳过已处理的项目。{Style.RESET_ALL}")
            else:
                print(f"{Fore.YELLOW}未发现有效历史记录，将重新开始处理。{Style.RESET_ALL}")

        logger.info(f"共需处理 {total_records} 条问答记录。")
        
        processed_count = 0
        skipped_count = 0
        error_count = 0
        
        # 如果恢复了进度，更新统计信息（假设恢复的都是处理成功的）
        # 实际上我们需要遍历来准确统计，或者简单地只统计本次运行的
        # 这里我们只统计本次运行的新增处理，但在进度条显示时会考虑已处理的
        
        already_processed_count = loaded_count
        failed_rows = [] # 记录失败的行索引

        # --- 检测已有失败结果并询问是否重试 ---
        retry_rows = []  # 需要重试的行索引
        similarity_col_name = result_columns["similarity_result"][0]
        
        # 扫描已有结果，查找需要重试的记录
        for i in range(total_records):
            if excel_processor.has_result(i, result_columns):
                # 获取当前结果
                current_result = excel_processor.get_result(i, similarity_col_name)
                # 检查是否为失败状态
                if current_result in ["否", "错误", "不确定"]:
                    retry_rows.append(i)
        
        if retry_rows:
            from semantic_tester.ui.menu import MenuHandler
            print(f"\n{Fore.YELLOW}📊 检测到历史评估记录中有 {len(retry_rows)} 条结果为 '否'、'错误' 或 '不确定'{Style.RESET_ALL}")
            print(f"   总记录数: {total_records}")
            print(f"   需重新评估: {len(retry_rows)}")
            print()
            
            if MenuHandler.confirm_action(f"是否重新评估这 {len(retry_rows)} 条记录？", default=True):
                print(f"\n{Fore.CYAN}🔄 准备重新评估 {len(retry_rows)} 条记录...{Style.RESET_ALL}\n")
                
                # 使用重试行列表，跳过正常的处理逻辑
                for idx, row_index in enumerate(retry_rows, 1):
                    # 显示重试进度
                    print(f"{Fore.CYAN}📊 正在重新评估第 {idx}/{len(retry_rows)} 条记录 (行 {row_index + 1})...{Style.RESET_ALL}")
                    
                    result = self._process_single_row(
                        row_index=row_index,
                        total_records=total_records,
                        knowledge_base_dir=knowledge_base_dir,
                        column_mapping=column_mapping,
                        result_columns=result_columns,
                        output_path=output_path,
                        show_comparison_result=show_comparison_result,
                        excel_processor=excel_processor,
                        use_full_doc_match=use_full_doc_match,
                        is_retry=True
                    )
                    
                    if result == "processed":
                        processed_count += 1
                    elif result == "skipped":
                        skipped_count += 1
                    elif result == "error":
                        error_count += 1
                        failed_rows.append(row_index)
                    
                    # 定期保存中间结果（每10条）
                    if idx % 10 == 0:
                        excel_processor.save_intermediate_results(output_path, idx)
                
                # 保存重试结果
                excel_processor.save_final_results(output_path)
                
                # 显示重试结果汇总
                provider_name = self.provider_manager.get_current_provider_name() if self.provider_manager else "未知"
                current_provider = self.provider_manager.get_current_provider() if self.provider_manager else None
                model_name = getattr(current_provider, "model", "默认模型") if current_provider else "默认模型"
                
                CLIInterface.print_detailed_result_summary(
                    total=len(retry_rows),
                    processed=processed_count,
                    skipped=skipped_count,
                    errors=error_count,
                    file_path=excel_processor.excel_path,
                    output_path=output_path,
                    provider_name=provider_name,
                    model_name=model_name
                )
                
                print(f"\n{Fore.GREEN}✅ 重新评估完成！{Style.RESET_ALL}")
                return  # 完成重试后直接返回，不再继续常规处理
            else:
                print(f"\n{Fore.YELLOW}⏭️  跳过重新评估，继续处理未评估的记录...{Style.RESET_ALL}\n")

        # --- 预检（Dry Run）逻辑 ---
        # 仅当还有未处理记录时才询问
        if processed_count + already_processed_count < total_records:
            from semantic_tester.ui.menu import MenuHandler
            
            # 查找第一条未处理的记录
            first_unprocessed_index = -1
            for i in range(total_records):
                if not excel_processor.has_result(i, result_columns):
                    first_unprocessed_index = i
                    break
            
            if first_unprocessed_index != -1:
                if MenuHandler.confirm_action("是否先测试第一条未处理记录以验证配置？", default=True):
                    print(f"\n{Fore.CYAN}🔍 正在执行预检测试 (第 {first_unprocessed_index + 1} 条记录)...{Style.RESET_ALL}")
                    
                    # 执行测试
                    test_result = self._process_single_row(
                        row_index=first_unprocessed_index,
                        total_records=total_records,
                        knowledge_base_dir=knowledge_base_dir,
                        column_mapping=column_mapping,
                        result_columns=result_columns,
                        output_path=output_path,
                        show_comparison_result=True, # 强制显示测试结果
                        excel_processor=excel_processor,
                        use_full_doc_match=use_full_doc_match,
                        is_retry=False
                    )
                    
                    if test_result == "error":
                        print(f"\n{Fore.RED}❌ 预检测试失败！{Style.RESET_ALL}")
                        print("请检查 API 配置、网络连接或文档路径。")
                        if not MenuHandler.confirm_action("⚠️  警告：测试失败。是否仍要强行继续批量处理？", default=False):
                            print("操作已取消。")
                            return
                    else:
                        print(f"\n{Fore.GREEN}✅ 预检测试通过！{Style.RESET_ALL}")
                        if not MenuHandler.confirm_action("准备就绪，是否开始批量处理剩余记录？", default=True):
                            print("操作已取消。")
                            return
                        
                        # 如果测试通过，更新计数器（因为该行已被处理）
                        if test_result == "processed":
                            processed_count += 1
                        elif test_result == "skipped":
                            skipped_count += 1

        # 处理每一行数据
        for row_index in range(total_records):
            # 检查是否已处理
            if excel_processor.has_result(row_index, result_columns):
                # 如果已处理，跳过
                # 可以在这里打印一条跳过日志，或者静默跳过
                # 为了不刷屏，我们静默跳过，但在进度条上体现
                continue

            result = self._process_single_row(
                row_index=row_index,
                total_records=total_records,
                knowledge_base_dir=knowledge_base_dir,
                column_mapping=column_mapping,
                result_columns=result_columns,
                output_path=output_path,
                show_comparison_result=show_comparison_result,
                excel_processor=excel_processor,
                use_full_doc_match=use_full_doc_match,
            )
            
            if result == "processed":
                processed_count += 1
            elif result == "skipped":
                skipped_count += 1
            else:
                error_count += 1
                failed_rows.append(row_index)

        # 保存最终结果
        excel_processor.save_final_results(output_path)
        
        # 处理失败的记录 (如果有)
        if failed_rows:
             self._handle_failed_rows(
                failed_rows,
                knowledge_base_dir,
                column_mapping,
                result_columns,
                output_path,
                show_comparison_result,
                excel_processor,
                use_full_doc_match=use_full_doc_match
            )
            # 更新错误计数（减去重试成功的）
            # 注意：这里的逻辑稍微有点复杂，因为 _handle_failed_rows 可能会递归
            # 为了简化，我们不再更新这里的 error_count，因为摘要已经打印过了
            # 如果需要更新摘要，应该在 _handle_failed_rows 结束后再次打印摘要，或者不打印初始摘要
            # 现在的流程是：打印初始摘要 -> 询问重试 -> 重试 -> 打印重试结果
            
        # 再次保存（以防重试修改了结果）
        excel_processor.save_final_results(output_path)
        
        # 显示处理摘要
        # 注意：这里的统计数据只包含本次运行处理的数据
        # 如果需要包含之前的，可以加上 already_processed_count
        
        # 获取当前供应商信息
        provider_name = "未知"
        model_name = "未知"
        if self.provider_manager:
            current_provider = self.provider_manager.get_current_provider()
            if current_provider:
                provider_name = current_provider.name
                model_name = getattr(current_provider, "model", "默认模型")
        elif self.api_handler:
            provider_name = "Gemini (Legacy)"
            model_name = self.api_handler.model_name

        CLIInterface.print_detailed_result_summary(
            total=total_records,
            processed=processed_count + already_processed_count, # 包含历史处理的
            skipped=skipped_count,
            errors=error_count,
            file_path=excel_processor.excel_path,
            output_path=output_path,
            provider_name=provider_name,
            model_name=model_name
        )
        
        # 处理失败的记录
        if error_count > 0:
            # 收集失败的行索引（这里需要重新扫描一下或者在循环中记录）
            # 为了简单起见，我们假设 error_count > 0 时需要处理
            # 但实际上我们需要具体的行索引。
            # 让我们修改上面的循环来收集 failed_rows
            pass # 逻辑已移至下方 _handle_failed_rows 调用

    def _handle_failed_rows(
        self,
        failed_rows: list,
        knowledge_base_dir: str,
        column_mapping: dict,
        result_columns: dict,
        output_path: str,
        show_comparison_result: bool,
        excel_processor: "ExcelProcessor",
        use_full_doc_match: bool = False,
    ):
        """
        处理失败的行
        """
        from semantic_tester.ui import CLIInterface
        from semantic_tester.ui.menu import MenuHandler
        
        if not failed_rows:
            return

        print(f"\n{Fore.YELLOW}⚠️ 有 {len(failed_rows)} 条记录处理失败。{Style.RESET_ALL}")
        
        if not MenuHandler.confirm_action("是否尝试重试这些失败的记录？"):
            return

        # 询问是否更换 AI 供应商
        if MenuHandler.confirm_action("是否更换 AI 供应商进行重试？"):
            if self.provider_manager:
                selected_provider_id = CLIInterface.select_ai_provider(
                    self.provider_manager
                )
                if selected_provider_id:
                    print(f"{Fore.GREEN}已切换供应商，准备重试...{Style.RESET_ALL}")
            else:
                print(f"{Fore.RED}供应商管理器不可用，无法切换。{Style.RESET_ALL}")

        print(f"\n{Fore.GREEN}开始重试 {len(failed_rows)} 条失败记录...{Style.RESET_ALL}")
        
        new_failed_rows = []
        retry_processed_count = 0
        
        for row_index in failed_rows:
            result = self._process_single_row(
                row_index=row_index,
                total_records=len(failed_rows), # 这里的总数显示为待重试数可能更直观，但为了保持一致性...
                # 或者我们可以传递一个特殊的 flag 让 _process_single_row 显示 "重试进度"
                knowledge_base_dir=knowledge_base_dir,
                column_mapping=column_mapping,
                result_columns=result_columns,
                output_path=output_path,
                show_comparison_result=show_comparison_result,
                excel_processor=excel_processor,
                use_full_doc_match=use_full_doc_match,
                is_retry=True
            )
            
            if result == "error":
                new_failed_rows.append(row_index)
            elif result == "processed":
                retry_processed_count += 1
        
        # 保存最终结果
        excel_processor.save_final_results(output_path)
        
        print(f"\n{Fore.CYAN}重试完成。成功修复: {retry_processed_count} 条，仍失败: {len(new_failed_rows)} 条。{Style.RESET_ALL}")
        
        if new_failed_rows:
            if MenuHandler.confirm_action("仍有失败记录，是否继续重试？"):
                self._handle_failed_rows(
                    new_failed_rows,
                    knowledge_base_dir,
                    column_mapping,
                    result_columns,
                    output_path,
                    show_comparison_result,
                    excel_processor,
                    use_full_doc_match=use_full_doc_match
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
        use_full_doc_match: bool = False,
        **kwargs
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
        # 延迟导入
        from semantic_tester.ui import CLIInterface  # noqa: F811
        from semantic_tester.utils import ValidationUtils  # noqa: F811
        import time

        row_number = row_index + 1
        
        # 如果是重试模式，进度显示略有不同（可选）
        if kwargs.get("is_retry", False):
            logger.info(f"正在重试第 {row_number} 行...")
        else:
            # 显示处理进度
            CLIInterface.print_progress(row_number, total_records)

        # 获取行数据
        row_data = excel_processor.get_row_data(row_index, column_mapping)

        # 验证行数据
        validation_errors = ValidationUtils.validate_row_data(row_data)
        if validation_errors:
            self._handle_validation_errors(
                row_index,
                row_number,
                total_records,
                validation_errors,
                result_columns,
                output_path,
                excel_processor,
            )
            return "skipped"

        # 读取知识库文档内容
        doc_content = self._read_document_content(
            knowledge_base_dir=knowledge_base_dir, 
            doc_name=row_data["doc_name"],
            use_full_doc_match=use_full_doc_match
        )

        if not doc_content:
            self._handle_missing_document(
                row_index,
                row_number,
                total_records,
                row_data["doc_name"],
                result_columns,
                output_path,
                excel_processor,
            )
            return "error"

        # 调用语义比对 API (带重试机制)
        max_retries = 3
        last_error = None
        
        for attempt in range(max_retries):
            try:
                result, reason = self._call_semantic_api(row_data, doc_content)

                # 检查结果是否有效
                if result != "错误":
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
                            ai_answer=row_data["ai_answer"],
                            result=result,
                            reason=reason,
                        )

                    # 保存中间结果
                    excel_processor.save_intermediate_results(output_path, row_number)

                    return "processed"
                
                # 如果结果是"错误"，记录警告并重试
                logger.warning(f"第 {row_number} 行处理返回错误 (尝试 {attempt + 1}/{max_retries}): {reason}")
                last_error = Exception(reason)
                
            except Exception as e:
                logger.warning(f"第 {row_number} 行发生异常 (尝试 {attempt + 1}/{max_retries}): {e}")
                last_error = e
            
            # 如果不是最后一次尝试，等待后重试
            if attempt < max_retries - 1:
                time.sleep(1)
        
        # 所有重试都失败
        self._handle_processing_error(
            row_index, row_number, last_error or Exception("未知错误"), result_columns, output_path, excel_processor
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
        """调用语义比对API"""
        # 获取流式输出和思维链配置
        enable_stream = getattr(self, "enable_stream", False)
        enable_thinking = getattr(self, "enable_thinking", True)
        
        # 优先使用新的供应商管理器，保持向后兼容
        if self.provider_manager:
            return self.provider_manager.check_semantic_similarity(
                question=row_data["question"],
                ai_answer=row_data["ai_answer"],
                source_document=doc_content,
                stream=enable_stream,  # 传递流式输出配置
                show_thinking=enable_thinking,  # 默认开启思维链（由环境变量控制）
            )
        elif self.api_handler:
            # 延迟导入
            from semantic_tester.api import check_semantic_similarity  # noqa: F811

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
        self, knowledge_base_dir: str, doc_name: str, use_full_doc_match: bool = False
    ) -> Optional[str]:
        """
        读取文档内容

        Args:
            knowledge_base_dir: 知识库目录
            doc_name: 文档名称，如果为空则读取整个文件夹的所有文档
            use_full_doc_match: 是否强制使用全量文档匹配

        Returns:
            Optional[str]: 文档内容，读取失败返回 None
        """
        # 延迟导入
        from semantic_tester.utils import FileUtils  # noqa: F811

        # 如果启用全量文档匹配，直接读取整个文件夹
        if use_full_doc_match:
            return self._read_all_documents_in_folder(knowledge_base_dir)

        # 如果文档名称为空，读取整个文件夹的所有文档
        if not doc_name or doc_name.strip() == "":
            logger.info("文档名称为空，将读取整个知识库文件夹的所有文档")
            return self._read_all_documents_in_folder(knowledge_base_dir)

        # 确保文档名称有 .md 扩展名
        if not doc_name.lower().endswith(".md"):
            doc_name += ".md"

        # 查找文档文件（首先尝试直接路径，保持与原始代码一致）
        doc_path = FileUtils.find_file_by_name(
            knowledge_base_dir, doc_name, recursive=False
        )
        if not doc_path:
            logger.warning(f"未找到文档: {doc_name}，尝试读取整个知识库...")
            return self._read_all_documents_in_folder(knowledge_base_dir)

        # 读取文档内容
        content = FileUtils.read_file_content(doc_path)
        if content is None:
            logger.error(f"无法读取文档内容: {doc_path}")
            return None

        logger.debug(f"成功读取文档: {doc_name} ({len(content)} 字符)")
        return content

    def _read_all_documents_in_folder(self, knowledge_base_dir: str) -> Optional[str]:
        """
        读取知识库文件夹中的所有文档内容

        Args:
            knowledge_base_dir: 知识库目录

        Returns:
            Optional[str]: 合并后的所有文档内容，读取失败返回 None
        """
        # 延迟导入
        from semantic_tester.utils import FileUtils  # noqa: F811

        # 查找所有 Markdown 文件
        markdown_files = FileUtils.find_markdown_files(
            knowledge_base_dir, recursive=True
        )

        if not markdown_files:
            logger.warning(f"知识库目录中没有找到任何文档: {knowledge_base_dir}")
            return None

        logger.info(f"在知识库中找到 {len(markdown_files)} 个文档，开始读取...")

        # 读取并合并所有文档内容
        all_content = []
        for file_path in markdown_files:
            content = FileUtils.read_file_content(file_path)
            if content:
                # 添加文档分隔符，标明文档来源
                file_name = os.path.basename(file_path)
                all_content.append(f"# 文档: {file_name}\n\n{content}")

        if not all_content:
            logger.error("无法读取任何文档内容")
            return None

        # 合并所有文档内容
        combined_content = "\n\n" + "=" * 80 + "\n\n".join(all_content)
        logger.info(
            f"成功读取并合并 {len(all_content)} 个文档，总字符数: {len(combined_content)}"
        )

        return combined_content

    def _show_startup_info(self):
        """显示启动信息，强调Dify Chat Tester集成"""
        from colorama import Fore, Style

        print(f"\n{Fore.CYAN}🚀 AI客服问答语义比对工具{Style.RESET_ALL}")
        print(f"{Fore.GREEN}🔗 完美集成 Dify Chat Tester{Style.RESET_ALL}")
        print()
        print("• 直接读取 Dify Chat Tester 输出文件")
        print("• 自动适配 Dify 格式列映射")
        print("• 智能检测并建议格式转换")
        print("• 支持多供应商语义评估")
        print()
        print(f"{Fore.YELLOW}💡 推荐工作流程：{Style.RESET_ALL}")
        print("1. 使用 Dify Chat Tester 生成测试数据")
        print("2. 本程序自动识别格式并评估语义质量")
        print("3. 生成详细的语义分析报告")
        print()

    def run_menu_mode(self):
        """运行菜单模式"""
        from semantic_tester.ui.menu import MenuHandler

        # 显示启动信息，强调Dify Chat Tester集成
        self._show_startup_info()

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
        print(f"✅ 已配置且可用: {validation_status['valid']} 个")
        print(f"❌ 已配置但无效: {validation_status['invalid']} 个")
        print(f"⚠️  未配置API密钥: {validation_status['unconfigured']} 个")

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
            # 优化状态描述
            status_text = result["status"]
            if status_text == "验证通过":
                status_text = "已配置且可用"
            elif status_text == "验证失败":
                status_text = "已配置但无效"
            elif status_text == "未配置":
                status_text = "未配置API密钥"

            print(f"   状态: {status_text}")
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
            models = provider_info.get("models", [])
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


def _display_completion_message():
    """显示完成信息"""
    from semantic_tester.ui.terminal_ui import print_summary_panel
    # 这里我们没有具体的统计数据，所以只显示完成提示
    # 或者我们可以修改 print_summary_panel 使其更通用
    # 暂时保持简单的美化输出
    print(f"\n{Fore.GREEN}=" * 60 + Style.RESET_ALL)
    print(f"{Fore.GREEN}✅ 所有处理已完成！{Style.RESET_ALL}")
    print(f"{Fore.GREEN}=" * 60 + Style.RESET_ALL)


def main():
    """主程序入口"""
    # 延迟导入以避免循环依赖
    from semantic_tester.ui.terminal_ui import print_welcome
    
    # 显示程序标头
    print_welcome()
    
    try:
        # 创建并初始化应用实例
        app = _create_and_initialize_app()
        if not app:
            sys.exit(1)

        # 检测是否为打包后的程序
        is_frozen = getattr(sys, "frozen", False)

        if is_frozen:
            # 打包后的程序 - 始终进入交互模式
            app.run_interactive_mode()
        else:
            # 开发环境 - 支持命令行参数
            if len(sys.argv) > 1:
                # 处理命令行参数
                if _handle_help_argument():
                    sys.exit(0)

                # 命令行模式处理
                _run_command_line_mode(app)
            else:
                # 交互式菜单模式
                app.run_interactive_mode()

    except KeyboardInterrupt:
        print(f"\n\n{Fore.YELLOW}⚠️  用户取消操作，程序退出{Style.RESET_ALL}")
        sys.exit(0)
    except Exception as e:
        logger.exception(f"程序运行时发生未捕获的异常: {e}")
        print(f"\n{Fore.RED}❌ 程序运行出错: {e}{Style.RESET_ALL}")
        sys.exit(1)


def _create_and_initialize_app() -> Optional[SemanticTestApp]:
    """
    创建并初始化应用实例

    Returns:
        SemanticTestApp or None: 初始化成功返回应用实例，失败返回None
    """
    import threading
    import time

    # 首先显示标题和应用信息（在加载动画之前）
    LoggerUtils.print_startup_banner()

    # 显示加载动画
    loading = True
    spinner_chars = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]

    def show_loading():
        """显示加载动画"""
        idx = 0
        while loading:
            print(
                f"\r{Fore.CYAN}{spinner_chars[idx % len(spinner_chars)]} 正在启动程序，请稍候...{Style.RESET_ALL}",
                end="",
                flush=True,
            )
            idx += 1
            time.sleep(0.1)

    # 启动加载动画线程
    loading_thread = threading.Thread(target=show_loading, daemon=True)
    loading_thread.start()

    try:
        # 创建并初始化应用
        app = SemanticTestApp()
        if not app.initialize():
            return None

        return app
    finally:
        # 停止加载动画
        loading = False
        loading_thread.join(timeout=1.0)
        # 清除加载行 - 确保完全清除
        print("\r" + " " * 80 + "\r", end="", flush=True)


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
    # 延迟导入
    from semantic_tester.ui import CLIInterface  # noqa: F811

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

    # 获取全量文档匹配配置
    use_full_doc_match = app.env_manager.get_use_full_doc_match()
    if use_full_doc_match:
        print(f"{Fore.GREEN}✅ 已启用全量文档匹配模式{Style.RESET_ALL}")

    # 开始处理
    app.process_data(
        knowledge_base_dir=knowledge_base_dir,
        column_mapping=column_mapping,
        result_columns=result_columns,
        output_path=output_path,
        show_comparison_result=False,
        use_full_doc_match=use_full_doc_match,
    )

    # 显示完成信息
    _display_completion_message()


def _validate_and_load_excel(app: SemanticTestApp, excel_path: str) -> bool:
    """
    验证并加载Excel文件

    Returns:
        bool: 成功返回True
    """
    # 延迟导入
    from semantic_tester.utils import ValidationUtils  # noqa: F811
    from semantic_tester.excel import ExcelProcessor  # noqa: F811

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
