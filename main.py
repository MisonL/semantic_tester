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

import warnings
import logging
import os
import sys
import threading

# 过滤不必要的警告 (特别是 Google API 的 Python 版本警告)
warnings.filterwarnings("ignore", category=FutureWarning, module="google.api_core")
warnings.filterwarnings("ignore", category=UserWarning, module="google.api_core")
warnings.filterwarnings("ignore", category=FutureWarning, module="google.auth")

from typing import Optional, TYPE_CHECKING, List, Tuple
from colorama import Fore, Style

# 导入版本信息

# 延迟导入优化：只导入最基本的模块
from semantic_tester.config import EnvManager, Config
from semantic_tester.utils import LoggerUtils

if TYPE_CHECKING:
    from semantic_tester.api import check_semantic_similarity  # noqa: F401
    from semantic_tester.api.provider_manager import ProviderManager  # noqa: F401
    from semantic_tester.api.base_provider import AIProvider  # noqa: F401
    from semantic_tester.excel import ExcelProcessor  # noqa: F401
    from semantic_tester.ui import CLIInterface  # noqa: F401
    from semantic_tester.utils import FileUtils, ValidationUtils  # noqa: F401

# 设置日志 - 使用简洁模式
LoggerUtils.setup_logging(quiet_console=True)
logger = logging.getLogger(__name__)


class SemanticTestApp:
    """语义测试应用主类"""

    def __init__(
        self,
        env_manager: Optional["EnvManager"] = None,
        config: Optional["Config"] = None,
    ):
        """初始化应用

        Args:
            env_manager: 环境管理器实例（可选，默认创建新实例）
            config: 配置实例（可选，默认创建新实例）
        """
        self.env_manager = env_manager if env_manager is not None else EnvManager()
        self.config = config if config is not None else Config()
        self.provider_manager: Optional["ProviderManager"] = None
        self.excel_processor: Optional["ExcelProcessor"] = None
        self._kb_cache: Optional[str] = None  # 知识库内容缓存

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
                "configured": len(
                    self.provider_manager.get_configured_providers_list()
                ),
                "current": (
                    self.provider_manager.get_current_provider_name()
                    if self.provider_manager.get_current_provider()
                    else "无"
                ),
            }
            print()  # 添加空行，避免与前面内容同行
            LoggerUtils.print_provider_summary(providers_info)

            # 如果没有配置的供应商，显示提示
            if not self.provider_manager.get_configured_providers_list():
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

        # 供应商选择和配置 (多渠道驱动)
        if self.provider_manager:
            # 直接确定供应商配置
            print(f"\n{Fore.CYAN}🔍 正在执行 API 密钥有效性预检...{Style.RESET_ALL}")
            validation_results = (
                self.provider_manager.validate_all_configured_channels()
            )

            # 使用 Rich 表格展示验证结果
            from rich.table import Table
            from rich.console import Console
            from rich import box

            console = Console()
            table = Table(title="AI 渠道验证报告", box=box.ROUNDED, expand=True)
            table.add_column("ID", justify="center", style="cyan")
            table.add_column("渠道名称", style="white")
            table.add_column("类型", justify="center")
            table.add_column("状态", justify="center")
            table.add_column("说明信息", style="dim")

            for res in validation_results:
                status_str = (
                    "[green]✅ 有效[/green]" if res["valid"] else "[red]❌ 无效[/red]"
                )
                table.add_row(
                    res["id"],
                    res["name"],
                    res.get("type", "unknown"),
                    status_str,
                    res["message"],
                )

            console.print(table)

            # 过滤通过验证的配置
            provider_configs = self.provider_manager.get_preset_channel_configs(
                verified_only=True
            )

            if not provider_configs:
                print(
                    f"\n{Fore.RED}❌ 错误: 没有任何渠道通过 API 验证，请检查您的 Key 设置。{Style.RESET_ALL}"
                )
                return

            print(
                f"\n{Fore.GREEN}🚀 验证完成：即将使用 {len(provider_configs)} 个有效渠道启动并行处理。{Style.RESET_ALL}"
            )
        from semantic_tester.ui.menu import MenuHandler

        # 获取 Excel 文件和知识库目录
        excel_path = CLIInterface.get_excel_file()
        knowledge_base_dir = CLIInterface.get_knowledge_base_dir()
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

        # 确认并获取输出路径
        default_output_path = self.config.get_default_output_path(excel_path)
        output_path = CLIInterface.get_output_path(default_output_path)
        self.config.ensure_output_dir(output_path)

        # 获取评估设置
        show_comparison = (
            True if use_auto_config else CLIInterface.ask_show_comparison_result()
        )

        use_full_doc_match = MenuHandler.confirm_action(
            "是否启用全量文档匹配？", default=False
        )
        enable_stream = MenuHandler.confirm_action("是否启用流式输出？", default=True)

        if not provider_configs:
            print("❌ 操作已取消或未选中任何供应商。")
            return

        # 执行处理
        self.process_data(
            knowledge_base_dir=knowledge_base_dir,
            column_mapping=column_mapping,
            result_columns=result_columns,
            output_path=output_path,
            show_comparison_result=show_comparison,
            enable_stream=enable_stream,
            use_full_doc_match=use_full_doc_match,
            provider_configs=provider_configs,
            save_interval=self.config.auto_save_interval,
        )
        return  # 结束 run_interactive_mode

    def process_data(
        self,
        knowledge_base_dir: str,
        column_mapping: dict,
        result_columns: dict,
        output_path: str,
        show_comparison_result: bool,
        enable_stream: bool = False,
        use_full_doc_match: bool = False,
        provider_configs: Optional[List[Tuple["AIProvider", int]]] = None,
        save_interval: int = 10,
    ):
        """处理数据 (基于队列的多渠道并发)"""
        import queue
        import time

        # 保存流式输出 / 思维链配置
        self.enable_stream = enable_stream
        try:
            self.enable_thinking = self.env_manager.get_enable_thinking()
        except AttributeError:
            self.enable_thinking = True

        from semantic_tester.ui import CLIInterface

        excel_processor = self._get_excel_processor_or_error()
        if not excel_processor:
            return

        total_records = excel_processor.get_total_records()

        # 尝试加载现有结果以恢复进度
        loaded_count = 0
        if os.path.exists(output_path):
            print(f"\n{Fore.CYAN}检测到现有输出文件，正在检查进度...{Style.RESET_ALL}")
            loaded_count = excel_processor.load_existing_results(
                output_path, result_columns
            )
            if loaded_count > 0:
                print(
                    f"{Fore.GREEN}已恢复 {loaded_count} 条历史记录，将跳过已处理的项目。{Style.RESET_ALL}"
                )
            else:
                print(
                    f"{Fore.YELLOW}未发现有效历史记录，将重新开始处理。{Style.RESET_ALL}"
                )

        logger.info(f"共需处理 {total_records} 条问答记录。")
        self._kb_cache = None  # 每次任务开始前清理缓存

        # 准备任务队列
        pending_rows = []
        for i in range(total_records):
            if not excel_processor.has_result(i, result_columns):
                pending_rows.append(i)

        if not pending_rows:
            print(f"{Fore.GREEN}✅ 所有记录已处理完成。{Style.RESET_ALL}")
            return

        task_queue = queue.Queue()
        for r in pending_rows:
            task_queue.put(r)

        # 默认供应商回退
        if not provider_configs:
            current_p = self.provider_manager.get_current_provider()
            provider_configs = [(current_p, 1)] if current_p else []

        if not provider_configs:
            logger.error("无可用供应商配置")
            return

        total_concurrency = sum(conf[1] for conf in provider_configs)

        # 启动 UI
        from semantic_tester.ui.worker_ui import WorkerTableUI

        ui = WorkerTableUI(total_records=total_records, concurrency=total_concurrency)
        ui.processed_count = loaded_count
        ui.progress.update(ui.main_task, completed=loaded_count)

        stop_event = threading.Event()

        def _provider_worker_loop(provider, ui):
            thread_id = threading.get_ident()
            p_name = provider.name

            while not task_queue.empty() and not stop_event.is_set():
                try:
                    row_idx = task_queue.get_nowait()
                except queue.Empty:
                    break

                # 获取当前行问题用于展示
                row_data_preview = excel_processor.get_row_data(row_idx, column_mapping)
                current_question = row_data_preview.get("question", "")

                ui.update_worker(
                    thread_id,
                    "分析中...",
                    row_idx,
                    provider_name=p_name,
                    question=current_question,
                )

                # 更新回调以包含问题
                def worker_stream_callback(content):
                    """实时更新 worker UI 预览"""
                    ui.update_worker(
                        thread_id,
                        "🚀 分析中...",
                        row_idx,
                        preview=content,
                        provider_name=p_name,
                        question=current_question,
                    )

                try:
                    # 并发模式下静默处理，以免弄乱 UI
                    result = self._process_single_row(
                        row_index=row_idx,
                        total_records=total_records,
                        knowledge_base_dir=knowledge_base_dir,
                        column_mapping=column_mapping,
                        result_columns=result_columns,
                        output_path=output_path,
                        show_comparison_result=False,
                        excel_processor=excel_processor,
                        use_full_doc_match=use_full_doc_match,
                        quiet=True,
                        provider_id=provider.id,
                        stream_callback=worker_stream_callback,  # 注入回调
                    )

                    if result == "processed":
                        similarity_col = result_columns["similarity_result"][0]
                        brief_result = excel_processor.get_result(
                            row_idx, similarity_col
                        )
                        ui.update_worker(
                            thread_id,
                            "完成",
                            row_idx,
                            preview=f"[{brief_result}]",
                            question=current_question,
                        )
                        ui.increment_progress("processed")
                    elif result == "skipped":
                        ui.update_worker(
                            thread_id, "跳过", row_idx, question=current_question
                        )
                        ui.increment_progress("skipped")
                    else:
                        ui.update_worker(
                            thread_id, "错误", row_idx, question=current_question
                        )
                        ui.increment_progress("error")

                except Exception as e:
                    logger.error(f"Worker [{p_name}] 异常: {e}")
                    ui.update_worker(
                        thread_id,
                        f"错误: {str(e)[:15]}",
                        row_idx,
                        question=(
                            current_question if "current_question" in locals() else ""
                        ),
                    )
                    ui.increment_progress("error")
                finally:
                    # 处理自动保存 (每处理 N 条记录保存一次，防止长时间中断丢失)
                    processed_total = (
                        ui.processed_count + ui.error_count + ui.skipped_count
                    )
                    if processed_total > 0 and processed_total % save_interval == 0:
                        excel_processor.save_intermediate_results(
                            output_path, processed_total
                        )
                    task_queue.task_done()

        # 启动线程
        worker_threads = []
        for provider, count in provider_configs:
            for _ in range(count):
                t = threading.Thread(
                    target=_provider_worker_loop, args=(provider, ui), daemon=True
                )
                t.start()
                worker_threads.append(t)

        # 临时提高日志等级，避免干扰 Live UI
        root_logger = logging.getLogger()
        old_level = root_logger.level

        try:
            with ui.run_live():
                # 为了 UI 稳定，将控制台输出日志设为 ERROR
                root_logger.setLevel(logging.ERROR)

                # 等待任务队列清空或UI完成
                while not ui.is_finished:
                    if stop_event.is_set():
                        break
                    time.sleep(0.5)
        except KeyboardInterrupt:
            root_logger.setLevel(old_level)  # 恢复日志以便显示中断信息
            print(
                f"\n\n{Fore.YELLOW}⚠️  检测到中断，正在终止并保存记录...{Style.RESET_ALL}"
            )
            stop_event.set()
        finally:
            root_logger.setLevel(old_level)

        # 等待所有线程退出
        for t in worker_threads:
            t.join(timeout=3.0)

        # 确保保存最终结果
        excel_processor.save_final_results(output_path)

        # 打印详细结果摘要
        # 尝试汇总供应商信息以便显示
        used_provider_names = list(set(conf[0].name for conf in provider_configs))
        display_provider = (
            used_provider_names[0] if len(used_provider_names) == 1 else "多渠道混合"
        )

        CLIInterface.print_detailed_result_summary(
            total=total_records,
            processed=ui.processed_count,
            skipped=ui.skipped_count,
            errors=ui.error_count,
            file_path=excel_processor.excel_path,
            output_path=output_path,
            provider_name=display_provider,
            model_name=(
                "混合模型"
                if len(used_provider_names) > 1
                else getattr(provider_configs[0][0], "model", "-")
            ),
        )

        # 处理失败的记录
        if ui.error_count > 0:
            # 扫描 pending_rows 中仍然失败的记录
            failed_rows = []
            for row_idx in pending_rows:
                if excel_processor.has_result(row_idx, result_columns):
                    # 检查结果是否为错误
                    similarity_col = result_columns["similarity_result"][0]
                    if excel_processor.get_result(row_idx, similarity_col) == "错误":
                        failed_rows.append(row_idx)
                # 仅重试明确标记为"错误"的记录，未处理的记录（如中断导致）将在下次运行时继续处理
                # else:
                #    failed_rows.append(row_idx)

            if failed_rows:
                self._handle_failed_rows(
                    failed_rows=failed_rows,
                    knowledge_base_dir=knowledge_base_dir,
                    column_mapping=column_mapping,
                    result_columns=result_columns,
                    output_path=output_path,
                    show_comparison_result=show_comparison_result,
                    excel_processor=excel_processor,
                    use_full_doc_match=use_full_doc_match,
                )

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
        处理失败的行（迭代模式）
        """
        from semantic_tester.ui import CLIInterface
        from semantic_tester.ui.menu import MenuHandler

        current_failed_rows = failed_rows

        while current_failed_rows:
            if not current_failed_rows:
                break

            print(
                f"\n{Fore.YELLOW}⚠️ 有 {len(current_failed_rows)} 条记录处理失败。{Style.RESET_ALL}"
            )

            if not MenuHandler.confirm_action("是否尝试重试这些失败的记录？"):
                break

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

            print(
                f"\n{Fore.GREEN}开始重试 {len(current_failed_rows)} 条失败记录...{Style.RESET_ALL}"
            )

            new_failed_rows = []
            retry_processed_count = 0

            try:
                for idx, row_index in enumerate(current_failed_rows, 1):
                    result = self._process_single_row(
                        row_index=row_index,
                        total_records=len(current_failed_rows),
                        knowledge_base_dir=knowledge_base_dir,
                        column_mapping=column_mapping,
                        result_columns=result_columns,
                        output_path=output_path,
                        show_comparison_result=show_comparison_result,
                        excel_processor=excel_processor,
                        use_full_doc_match=use_full_doc_match,
                        is_retry=True,
                    )

                    if result == "error":
                        new_failed_rows.append(row_index)
                    elif result == "processed":
                        retry_processed_count += 1

                    # 定期保存中间结果（每10条）
                    if idx % 10 == 0:
                        excel_processor.save_intermediate_results(
                            output_path, retry_processed_count
                        )

            except KeyboardInterrupt:
                print(
                    f"\n\n{Fore.YELLOW}⚠️  用户中断重试。正在保存当前进度...{Style.RESET_ALL}"
                )
                excel_processor.save_final_results(output_path)
                print(f"{Fore.GREEN}✅ 进度已保存到: {output_path}{Style.RESET_ALL}")
                raise

            # 保存最终结果
            excel_processor.save_final_results(output_path)

            print(
                f"\n{Fore.CYAN}重试完成。成功修复: {retry_processed_count} 条，仍失败: {len(new_failed_rows)} 条。{Style.RESET_ALL}"
            )

            # 更新失败列表
            current_failed_rows = new_failed_rows

            if current_failed_rows:
                if not MenuHandler.confirm_action("仍有失败记录，是否继续重试？"):
                    break
            else:
                print(f"{Fore.GREEN}✅ 所有失败记录已修复！{Style.RESET_ALL}")
                break

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
        provider_id: Optional[str] = None,
        stream_callback: Optional[callable] = None,  # 新增回调参数
        **kwargs,
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
            stream_callback: 流式输出回调函数

        Returns:
            str: 处理结果状态 ("processed", "skipped", "error")
        """
        # 延迟导入
        from semantic_tester.ui import CLIInterface  # noqa: F811
        from semantic_tester.utils import ValidationUtils  # noqa: F811
        import time

        row_number = row_index + 1

        # 检查是否静默模式 (并发执行时不打印进度)
        quiet = kwargs.get("quiet", False)

        # 如果是重试模式，进度显示略有不同（可选）
        if kwargs.get("is_retry", False):
            logger.info(f"正在重试第 {row_number} 行...")
        elif not quiet:
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
                quiet=quiet,
            )
            return "skipped"

        # 读取知识库文档内容
        doc_content = self._read_document_content(
            knowledge_base_dir=knowledge_base_dir,
            doc_name=row_data["doc_name"],
            use_full_doc_match=use_full_doc_match,
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
                quiet=quiet,
            )
            return "error"

        # 调用语义比对 API (带重试机制)
        max_retries = 3
        last_error = None

        for attempt in range(max_retries):
            try:
                # 计算实际是否启用流式 (并发模式quiet=True时通常关闭，但为了UI预览，我们需要开启流并捕获内容)
                # 如果提供了 stream_callback，则强制启用流式，但通过 callback 处理输出而不是打印到控制台
                actual_stream = getattr(self, "enable_stream", False) or (
                    stream_callback is not None
                )

                # 调用 API
                result, reason = self._call_semantic_api(
                    row_data,
                    doc_content,
                    enable_stream=actual_stream,
                    provider_id=provider_id,
                    stream_callback=stream_callback,  # 传递回调函数
                )

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

                    # 保存中间结果 (非静默模式下)
                    if not quiet:
                        excel_processor.save_intermediate_results(
                            output_path, row_number
                        )

                    return "processed"

                # 如果结果是"错误"，记录警告并重试
                logger.warning(
                    f"第 {row_number} 行处理返回错误 (尝试 {attempt + 1}/{max_retries}): {reason}"
                )
                last_error = Exception(reason)

            except Exception as e:
                logger.warning(
                    f"第 {row_number} 行发生异常 (尝试 {attempt + 1}/{max_retries}): {e}"
                )
                last_error = e

            # 如果不是最后一次尝试，等待后重试
            if attempt < max_retries - 1:
                time.sleep(1)

        # 所有重试都失败
        self._handle_processing_error(
            row_index,
            row_number,
            last_error or Exception("未知错误"),
            result_columns,
            output_path,
            excel_processor,
            quiet=quiet,
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
        quiet: bool = False,
    ):
        """
        处理验证错误
        """
        errors_str = "; ".join(validation_errors)
        error_msg = f"跳过第 {row_number}/{total_records} 条记录：{errors_str}"

        if not quiet:
            logger.warning(error_msg)

        excel_processor.save_result(
            row_index=row_index,
            result="跳过",
            reason=errors_str,
            result_columns=result_columns,
        )

        # 保存中间结果
        if not quiet and row_number % self.config.auto_save_interval == 0:
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
        quiet: bool = False,
    ):
        """
        处理文档缺失的情况
        """
        if not quiet:
            logger.warning(
                f"第 {row_number}/{total_records} 条记录：未找到对应的Markdown文件 ({doc_name})"
            )

        excel_processor.save_result(
            row_index=row_index,
            result="源文档未找到",
            reason=f"未找到对应的Markdown文件：{doc_name}",
            result_columns=result_columns,
        )

        # 每处理完一条记录就保存结果 (非静默模式下)
        if not quiet:
            excel_processor.save_intermediate_results(output_path, row_number)

    def _call_semantic_api(
        self,
        row_data: dict,
        doc_content: str,
        enable_stream: bool = False,
        provider_id: Optional[str] = None,
        stream_callback: Optional[callable] = None,
    ) -> tuple[str, str]:
        """调用语义比对API"""
        # 获取思维链配置
        enable_thinking = getattr(self, "enable_thinking", True)

        # 使用供应商管理器
        if self.provider_manager:
            return self.provider_manager.check_semantic_similarity(
                question=row_data["question"],
                ai_answer=row_data["ai_answer"],
                source_document=doc_content,
                provider_id=provider_id,  # 明确传递 provider_id
                stream=enable_stream,  # 使用传入的参数
                show_thinking=enable_thinking,
                stream_callback=stream_callback,  # 传递给 provider
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
        quiet: bool = False,
    ):
        """
        处理处理过程中的错误
        """
        if not quiet:
            logger.error(f"处理第 {row_number} 行时发生错误: {error}")

        excel_processor.save_result(
            row_index=row_index,
            result="错误",
            reason=f"处理异常: {str(error)}",
            result_columns=result_columns,
        )

        # 每处理完一条记录就保存结果 (非静默模式下)
        if not quiet:
            excel_processor.save_intermediate_results(output_path, row_number)

    def _read_document_content(
        self,
        knowledge_base_dir: str,
        doc_name: str,
        use_full_doc_match: bool = False,
    ) -> Optional[str]:
        """
        读取文档内容 (带缓存/全量匹配支持)

        Args:
            knowledge_base_dir: 知识库目录
            doc_name: 文档名称
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
            return self._read_all_documents_in_folder(knowledge_base_dir)

        # 确保文档名称有 .md 扩展名
        if not doc_name.lower().endswith(".md"):
            doc_name += ".md"

        # 查找文档文件
        doc_path = FileUtils.find_file_by_name(
            knowledge_base_dir, doc_name, recursive=False
        )
        if not doc_path:
            return self._read_all_documents_in_folder(knowledge_base_dir)

        # 读取文档内容
        return FileUtils.read_file_content(doc_path)

    def _read_all_documents_in_folder(self, knowledge_base_dir: str) -> Optional[str]:
        """读取文件夹内所有文档并合并 (带内存缓存)"""
        if self._kb_cache:
            return self._kb_cache

        # 延迟导入
        from semantic_tester.utils import FileUtils  # noqa: F811

        # 查找所有 Markdown 文件
        markdown_files = FileUtils.find_markdown_files(
            knowledge_base_dir, recursive=True
        )

        if not markdown_files:
            return None

        # 读取并合并所有文档内容
        all_content = FileUtils.read_all_markdowns(knowledge_base_dir)
        if all_content:
            self._kb_cache = all_content
            return all_content

        return None

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
                # 生成测试数据模板
                from semantic_tester.utils.dify_template_generator import create_dify_template_interactive
                create_dify_template_interactive()
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
                app.run_menu_mode()

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
    current_provider = app.provider_manager.get_current_provider()
    provider_configs = (
        [(current_provider, app.config.concurrency)] if current_provider else None
    )

    app.process_data(
        knowledge_base_dir=knowledge_base_dir,
        column_mapping=column_mapping,
        result_columns=result_columns,
        output_path=output_path,
        show_comparison_result=False,
        use_full_doc_match=use_full_doc_match,
        provider_configs=provider_configs,
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
        "similarity_result": ("语义是否与源文档相符", -1),
        "reason": ("判断依据", -1),
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



if __name__ == "__main__":
    main()
