"""
并发任务实时监控 UI 组件

提供类似 dify_chat_tester 的 Worker Table 和状态栏，
用于实时展示多线程并发处理的进度、worker 状态和回答预览。
"""

import time
import threading
from typing import Dict, Any, Optional

from rich.live import Live
from rich.table import Table
from rich.panel import Panel
from rich.console import Console, Group
from rich.progress import Progress, BarColumn, TextColumn, TimeRemainingColumn
from rich.text import Text
from rich import box


class WorkerTableUI:
    """并发处理实时监控界面"""

    def __init__(self, total_records: int, concurrency: int):
        self.console = Console()
        self.total_records = total_records
        self.concurrency = concurrency
        self.start_time = time.time()

        # 内部状态
        self.workers: Dict[int, Dict[str, Any]] = (
            {}
        )  # {thread_id: {status, record_idx, progress, preview, provider_name}}
        self.processed_count = 0
        self.error_count = 0
        self.skipped_count = 0

        # 互斥锁，保护状态更新
        self.lock = threading.Lock()

        # 定义进度条
        self.progress = Progress(
            TextColumn("[bold blue]{task.description}"),
            BarColumn(bar_width=None),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            TextColumn("•"),
            TextColumn("[bold cyan]{task.completed}/{task.total}"),
            TextColumn("•"),
            TimeRemainingColumn(),
            console=self.console,
            expand=True,
        )
        self.main_task = self.progress.add_task("总进度", total=total_records)

        # 是否已完成
        self.is_finished = False

    def update_worker(
        self,
        thread_id: int,
        status: str,
        record_idx: Optional[int] = None,
        preview: str = "",
        provider_name: str = "",
        question: str = "",
    ):
        """更新单个工作线程的状态"""
        with self.lock:
            if thread_id not in self.workers:
                self.workers[thread_id] = {
                    "id": len(self.workers) + 1,
                    "status": "等待中",
                    "record": "-",
                    "question": "",
                    "preview": "",
                    "provider": provider_name or "-",
                }

            if provider_name:
                self.workers[thread_id]["provider"] = provider_name

            if question:
                # Truncate question for display
                clean_question = question.replace("\n", " ").strip()
                if len(clean_question) > 20:
                    clean_question = clean_question[:17] + "..."
                self.workers[thread_id]["question"] = clean_question

            # 使用简洁的图标和状态（避免重复图标）
            status_clean = (
                status.replace("🚀", "")
                .replace("🤔", "")
                .replace("🔄", "")
                .replace("✅", "")
                .replace("❌", "")
                .strip()
            )
            if "分析" in status:
                self.workers[thread_id]["status"] = "[bold green]🔍 分析中[/]"
            elif "思考" in status:
                self.workers[thread_id]["status"] = "[bold cyan]💭 思考中[/]"
            elif "重试" in status:
                self.workers[thread_id]["status"] = "[bold yellow]🔄 重试[/]"
            elif "完成" in status:
                self.workers[thread_id]["status"] = "[dim green]✅ 完成[/]"
            elif "错误" in status:
                self.workers[thread_id]["status"] = "[bold red]❌ 错误[/]"
            elif "跳过" in status:
                self.workers[thread_id]["status"] = "[dim yellow]⏭️ 跳过[/]"
            else:
                self.workers[thread_id]["status"] = status_clean or status

            if record_idx is not None:
                self.workers[thread_id]["record"] = record_idx + 1
            if preview:
                # 智能解析 JSON 并优化显示
                import json
                import re

                clean_preview = preview
                try:
                    # 尝试解析完整或部分 JSON
                    json_match = re.search(r'\{[^{}]*"result"[^{}]*\}', preview)
                    json_str = json_match.group(0) if json_match else preview

                    if json_str.strip().startswith("{"):
                        data = json.loads(json_str)
                        if "result" in data:
                            result = str(data["result"]).strip()
                            reason = str(data.get("reason", "")).strip()

                            # 根据结果类型添加友好显示
                            if result in ("是", "yes", "Yes", "YES", "true", "True"):
                                result_text = "[green]是[/]"
                            elif result in ("否", "no", "No", "NO", "false", "False"):
                                result_text = "[red]否[/]"
                            elif result in (
                                "不确定",
                                "uncertain",
                                "Uncertain",
                                "unknown",
                            ):
                                result_text = "[yellow]不确定[/]"
                            else:
                                result_text = f"[cyan]{result}[/]"

                            # 组合最终显示：结果 | 理由
                            if reason:
                                if len(reason) > 30:
                                    reason = reason[:27] + "..."
                                clean_preview = f"{result_text} | {reason}"
                            else:
                                clean_preview = result_text
                except Exception:
                    # 解析失败时清理常见 JSON 字符
                    clean_preview = re.sub(r'[{}":]', "", preview)
                    clean_preview = clean_preview.replace("result", "").replace(
                        "reason", ""
                    )

                # 限制预览长度并清理换行
                clean_preview = clean_preview.replace("\n", " ").strip()
                if len(clean_preview) > 50:
                    clean_preview = clean_preview[:47] + "..."
                self.workers[thread_id]["preview"] = clean_preview

    def increment_progress(self, status: str = "processed"):
        """增加总进度计数"""
        with self.lock:
            if status == "processed":
                self.processed_count += 1
            elif status == "error":
                self.error_count += 1
            elif status == "skipped":
                self.skipped_count += 1

            # 更新整体进度条
            completed = self.processed_count + self.error_count + self.skipped_count
            self.progress.update(self.main_task, completed=completed)

            if completed >= self.total_records:
                self.is_finished = True

    def _create_worker_table(self) -> Table:
        """创建 Worker 状态表格"""
        table = Table(
            box=box.ROUNDED,
            expand=True,
            show_header=True,
            header_style="bold magenta",
            border_style="blue",
        )
        table.add_column(
            "Worker", justify="center", style="cyan", width=6, no_wrap=True
        )
        table.add_column(
            "供应商", justify="left", style="green", width=14, no_wrap=True
        )
        table.add_column(
            "记录", justify="center", style="yellow", width=6, no_wrap=True
        )
        table.add_column(
            "当前问题", justify="left", style="white", width=20, no_wrap=True
        )
        table.add_column("状态", justify="center", width=12, no_wrap=True)
        table.add_column("回复预览", justify="left", style="dim", ratio=1, no_wrap=True)

        # 按逻辑 ID 排序显示
        for t_id in sorted(self.workers.keys(), key=lambda x: self.workers[x]["id"]):
            w = self.workers[t_id]
            # 清理供应商名称中的换行符
            provider_name = str(w["provider"]).replace("\n", " ").strip()
            # 清理状态中的换行符
            status_text = str(w["status"]).replace("\n", " ").strip()
            table.add_row(
                f"#{w['id']}",
                provider_name,
                str(w["record"]),
                w.get("question", ""),
                status_text,
                w["preview"],
            )
        return table

    def _create_status_panel(self) -> Panel:
        """创建底部状态面板"""
        from semantic_tester.utils.format_utils import FormatUtils

        elapsed = time.time() - self.start_time
        total_done = self.processed_count + self.error_count + self.skipped_count

        # 计算 TPS (Transactions Per Second)
        tps = total_done / elapsed if elapsed > 0 else 0

        # 使用智能时间格式化（自动切换 s/m/h）
        elapsed_str = FormatUtils.format_duration(elapsed)

        status_text = Text.assemble(
            ("⏱️  耗时: ", "bold white"),
            (elapsed_str, "cyan"),
            ("  |  ", "dim"),
            ("✅ 完成: ", "bold green"),
            (f"{self.processed_count}", "green"),
            ("  |  ", "dim"),
            ("⚠️ 错误: ", "bold red"),
            (f"{self.error_count}", "red"),
            ("  |  ", "dim"),
            ("⏩ 跳过: ", "bold yellow"),
            (f"{self.skipped_count}", "yellow"),
            ("  |  ", "dim"),
            ("⚡ TPS: ", "bold magenta"),
            (f"{tps:.2f} r/s", "magenta"),
        )

        return Panel(status_text, box=box.SIMPLE, border_style="dim")

    def get_renderable(self):
        """生成供 Live 渲染的组合组件"""
        return Group(
            self._create_worker_table(), self.progress, self._create_status_panel()
        )

    def __rich_console__(self, console: Console, options: Any):
        """实现 Rich 控制台协议，使对象本身可渲染"""
        yield self.get_renderable()

    def run_live(self):
        """返回 Live 上下文管理器实例"""
        return Live(
            self,
            refresh_per_second=4,
            console=self.console,
            screen=True,  # 使用全屏模式，彻底解决残影问题
        )
