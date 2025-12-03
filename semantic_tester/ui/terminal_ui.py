"""
终端界面美化模块
提供颜色、面板、图标等美化功能

参考 dify_chat_tester 项目设计
"""

import sys
from typing import Optional

import colorama
from rich import box
from rich.console import Console, Group
from rich.panel import Panel
from rich.prompt import Confirm
from rich.table import Table
from rich.text import Text

# 初始化 colorama（Windows 兼容）
colorama.init(autoreset=True)

# 设置控制台窗口标题（Windows）
if sys.platform == "win32":
    try:
        import ctypes
        ctypes.windll.kernel32.SetConsoleTitleW("semantic_tester - AI语义分析工具")
    except Exception:
        pass

# 创建全局控制台对象
console = Console()


# 自定义颜色主题
class Colors:
    """自定义颜色方案"""
    
    BACKGROUND = "#000000"  # 黑色背景
    PRIMARY = "#33d4ff"  # 亮蓝色
    SUCCESS = "#4ade80"  # 绿色
    WARNING = "#fbbf24"  # 黄色
    ERROR = "#f87171"  # 红色
    INFO = "#60a5fa"  # 信息蓝
    ACCENT = "#c084fc"  # 紫色
    TEXT = "#ffffff"  # 主文本色（纯白）
    MUTED = "#9ca3af"  # 次要文本色（浅灰）


# 图标定义
class Icons:
    """Unicode 图标"""
    
    SUCCESS = "✅"
    ERROR = "❌"
    WARNING = "⚠️"
    INFO = "ℹ️"
    LOADING = "⏳"
    SPARKLES = "✨"
    TARGET = "🎯"
    GEAR = "⚙️"
    DIAMOND = "💎"
    DOCUMENT = "📄"
    QUESTION = "❓"
    SEARCH = "🔍"
    MEMO = "📝"
    DATA = "📊"
    FOLDER = "📁"
    FILE = "📄"
    CHECKMARK = "✓"
    CROSS = "✗"
    ROBOT = "🤖"


def print_success(message: str):
    """打印成功信息"""
    success_text = Text()
    success_text.append(f"{Icons.SUCCESS} {message}", style=f"bold {Colors.SUCCESS}")
    
    success_panel = Panel(
        success_text, border_style=Colors.SUCCESS, box=box.ROUNDED, padding=(0, 1)
    )
    console.print(success_panel)


def print_error(message: str):
    """打印错误信息"""
    error_text = Text()
    error_text.append(f"{Icons.ERROR} {message}", style=f"bold {Colors.ERROR}")
    
    error_panel = Panel(
        error_text, border_style=Colors.ERROR, box=box.ROUNDED, padding=(0, 1)
    )
    console.print(error_panel)


def print_warning(message: str):
    """打印警告信息"""
    warning_text = Text()
    warning_text.append(f"{Icons.WARNING} {message}", style=f"bold {Colors.WARNING}")
    
    warning_panel = Panel(
        warning_text, border_style=Colors.WARNING, box=box.ROUNDED, padding=(0, 1)
    )
    console.print(warning_panel)


def print_info(message: str):
    """打印信息"""
    info_text = Text()
    info_text.append(f"{Icons.INFO} {message}", style=f"bold {Colors.INFO}")
    
    info_panel = Panel(
        info_text, border_style=Colors.INFO, box=box.ROUNDED, padding=(0, 1)
    )
    console.print(info_panel)


def print_input_prompt(message: str) -> str:
    """打印输入提示（美化的）"""
    text = Text()
    text.append(f"{Icons.GEAR} ", style=f"bold {Colors.ACCENT}")
    text.append(message + ": ", style=Colors.TEXT)
    # 打印提示符但不换行
    console.print(text, end="")
    
    try:
        # 使用内置 input 函数，确保退格键正常工作
        return input().strip()
    except KeyboardInterrupt:
        # 重新抛出中断异常，让程序退出
        raise


def print_welcome():
    """打印美化版的程序标题头"""
    console.print()
    
    # 标题
    title = Text(
        "🎯 AI客服问答语义比对工具",
        style="bold bright_white",
        justify="center",
    )
    
    # 组合
    content = Group(
        Text(""),  # Extra space above title
        title,
        Text(""),  # Extra space below title
    )
    
    header_panel = Panel(
        content,
        box=box.ROUNDED,
        border_style="bright_cyan",
        padding=(1, 4),
        width=55,
        expand=False,
    )
    
    console.print(header_panel)


def print_section_header(title: str, icon: str = Icons.TARGET):
    """打印章节标题"""
    text = Text()
    text.append(f"{icon} {title}", style="bold bright_cyan")
    console.print(text)
    console.print()


def print_provider_table(providers: list, configured_providers: list):
    """使用表格显示供应商列表"""
    # 创建表格
    table = Table(
        show_header=True,
        header_style="bold cyan",
        box=None,
        border_style="bright_cyan",
        padding=(0, 1),
    )
    
    table.add_column("序号", style="cyan", justify="center", width=6)
    table.add_column("供应商", style="white", width=20)
    table.add_column("状态", style="white", justify="center", width=12)
    
    for i, provider_info in enumerate(providers, 1):
        provider_name = provider_info["name"]
        is_configured = provider_info["configured"]
        is_current = provider_info.get("is_current", False)
        
        # 状态显示
        if is_configured:
            status = f"[bold green]{Icons.SUCCESS} 已配置[/bold green]"
        else:
            status = f"[dim]{Icons.ERROR} 未配置[/dim]"
        
        # 当前标记
        name_display = f"{provider_name} [bold yellow](当前)[/bold yellow]" if is_current else provider_name
        
        table.add_row(str(i), name_display, status)
    
    # 创建面板
    panel = Panel(
        table,
        title=f"[bold]🤖 AI 供应商选择[/bold]",
        subtitle=f"[dim]可用: {len(providers)} | 已配置: {len(configured_providers)}[/dim]",
        border_style="bright_cyan",
        box=box.ROUNDED,
        padding=(0, 1),
        width=55,
        expand=False,
    )
    
    console.print(panel)
    console.print()


def print_file_table(files: list, title: str = "Excel 文件列表"):
    """使用表格显示文件列表"""
    if not files:
        print_warning(f"当前目录没有找到 {title}")
        return
    
    # 创建表格
    table = Table(show_header=False, box=None, padding=(0, 1))
    table.add_column("序号", style="cyan", justify="center", width=8)
    table.add_column("文件名", style="white")
    
    for i, file_name in enumerate(files, 1):
        table.add_row(f"[{i}]", file_name)
    
    file_panel = Panel(
        table,
        title=f"[bold]{Icons.FOLDER} {title}[/bold]",
        border_style="bright_cyan",
        box=box.ROUNDED,
        padding=(0, 1),
        width=55,
        expand=False,
    )
    console.print(file_panel)
    console.print()


def print_column_table(columns: list, title: str = "Excel 文件中的列名"):
    """使用表格显示列名列表"""
    # 创建表格
    table = Table(show_header=False, box=None, padding=(0, 1))
    table.add_column("序号", style="cyan", justify="center", width=8)
    table.add_column("列名", style="white")
    
    for i, col_name in enumerate(columns, 1):
        table.add_row(f"[{i}]", str(col_name))
    
    column_panel = Panel(
        table,
        title=f"[bold]{Icons.FILE} {title}[/bold]",
        border_style=Colors.SUCCESS,
        box=box.ROUNDED,
        padding=(0, 1),
        width=55,
        expand=False,
    )
    console.print(column_panel)
    console.print()


def print_comparison_result_panel(doc_name: str, question: str, ai_answer: str, result: str, reason: str):
    """使用面板显示语义比对结果"""
    # 创建内容文本
    content = Text()
    
    # 文档名
    content.append(f"{Icons.DOCUMENT} 文档: ", style="bold yellow")
    content.append(f"{doc_name}\n\n", style="white")
    
    # 问题
    content.append(f"{Icons.QUESTION} 问题: ", style="bold yellow")
    question_text = question[:100] + "..." if len(question) > 100 else question
    content.append(f"{question_text}\n\n", style="white")
    
    # AI回答
    content.append(f"💬 回答: ", style="bold yellow")
    answer_text = ai_answer[:200] + "..." if len(ai_answer) > 200 else ai_answer
    content.append(f"{answer_text}\n\n", style="white")
    
    # 结果
    content.append(f"{Icons.SEARCH} 结果: ", style="bold yellow")
    if result == "是":
        content.append(f"{Icons.SUCCESS} {result}", style="bright_green")
    elif result == "否":
        content.append(f"{Icons.CROSS} {result}", style="bold red")
    else:
        content.append(f"{Icons.WARNING} {result}", style="bold yellow")
    content.append("\n\n", style="white")
    
    # 原因
    content.append(f"{Icons.MEMO} 原因: ", style="bold yellow")
    reason_text = reason[:200] + "..." if len(reason) > 200 else reason
    content.append(reason_text, style="dim white")
    
    # 创建面板
    panel = Panel(
        content,
        title="[bold]📊 语义比对结果[/bold]",
        border_style="bright_magenta",
        box=box.ROUNDED,
        padding=(1, 2),
    )
    
    console.print(panel)


def confirm(message: str, default: bool = True) -> bool:
    """显示确认提示"""
    return Confirm.ask(f"[bold]{Icons.QUESTION} {message}[/bold]", default=default)


def print_progress(current: int, total: int, message: Optional[str] = None):
    """打印进度信息"""
    percentage = (current / total * 100) if total > 0 else 0
    pending = total - current
    
    progress_text = Text()
    progress_text.append(f"{Icons.LOADING} ", style="bold cyan")
    progress_text.append("处理进度: ", style="bold white")
    progress_text.append(f"{current}/{total} ", style="bright_green")
    progress_text.append(f"({percentage:.1f}%)", style="bold yellow")
    progress_text.append(f" | 待处理: {pending}", style="dim white")
    
    if message:
        progress_text.append(f"\n{Icons.INFO} {message}", style="dim cyan")
    
    console.print(progress_text)


def print_summary_panel(total: int, processed: int, skipped: int, errors: int):
    """显示处理摘要面板"""
    success_rate = (processed / total * 100) if total > 0 else 0
    
    summary_text = Text()
    summary_text.append(f"{Icons.DATA} 处理统计\n\n", style="bold yellow")
    summary_text.append(f"  • 总记录数: ", style="white")
    summary_text.append(f"{total}\n", style="bold cyan")
    summary_text.append(f"  • 成功处理: ", style="white")
    summary_text.append(f"{processed}", style="bold green")
    summary_text.append(f" ({success_rate:.1f}%)\n", style="bright_green")
    summary_text.append(f"  • 跳过记录: ", style="white")
    summary_text.append(f"{skipped}\n", style="bold yellow")
    summary_text.append(f"  • 错误记录: ", style="white")
    summary_text.append(f"{errors}", style="bold red")
    
    summary_panel = Panel(
        summary_text,
        title="[bold]✅ 处理完成[/bold]",
        border_style=Colors.SUCCESS,
        box=box.DOUBLE,
        padding=(1, 2),
    )
    
    console.print(summary_panel)


def print_detailed_summary_panel(
    total: int,
    processed: int,
    skipped: int,
    errors: int,
    file_path: str,
    output_path: str,
    provider_name: str,
    model_name: str
):
    """显示详细的处理摘要面板"""
    success_rate = (processed / total * 100) if total > 0 else 0
    
    summary_text = Text()
    
    # 文件信息
    summary_text.append("📁 文件信息\n", style="bold yellow")
    summary_text.append(f"  • 输入文件: {file_path}\n", style="white")
    summary_text.append(f"  • 输出文件: {output_path}\n\n", style="white")
    
    # 模型配置
    summary_text.append("🤖 模型配置\n", style="bold yellow")
    summary_text.append(f"  • AI 供应商: {provider_name}\n", style="white")
    summary_text.append(f"  • 选用模型: {model_name}\n\n", style="white")
    
    # 执行统计
    summary_text.append("📊 执行统计\n", style="bold yellow")
    summary_text.append(f"  • 总记录数: {total}\n", style="white")
    summary_text.append(f"  • 成功处理: ", style="white")
    summary_text.append(f"{processed}", style="bold green")
    summary_text.append(f" ({success_rate:.1f}%)\n", style="bright_green")
    
    if skipped > 0:
        summary_text.append(f"  • 跳过记录: ", style="white")
        summary_text.append(f"{skipped}\n", style="bold yellow")
        
    if errors > 0:
        summary_text.append(f"  • 错误记录: ", style="white")
        summary_text.append(f"{errors}\n", style="bold red")
    
    summary_panel = Panel(
        summary_text,
        title="[bold]📋 执行信息汇总[/bold]",
        border_style="bright_magenta",
        box=box.ROUNDED,
        padding=(1, 2),
    )
    
    console.print()
    console.print(summary_panel)
    console.print()

class StreamDisplay:
    """流式输出显示管理器"""
    
    def __init__(self, title: str = "AI 思考中..."):
        self.title = title
        self.content = ""
        self.live = None
        self.panel = None
        
    def start(self):
        """开始显示"""
        from rich.live import Live
        
        self.panel = Panel(
            "",
            title=f"{Icons.ROBOT} {self.title}",
            border_style=Colors.PRIMARY,
            box=box.ROUNDED,
            padding=(1, 2),
            width=100,
        )
        self.live = Live(self.panel, console=console, refresh_per_second=10, transient=True)
        self.live.start()
        
    def update(self, new_content: str):
        """更新内容"""
        if self.live:
            self.content += new_content
            # 尝试解析JSON以美化显示
            display_content = self.content
            try:
                import json
                # 尝试查找完整的JSON对象
                if "{" in self.content and "}" in self.content:
                    # 简单的提取尝试
                    start = self.content.find("{")
                    end = self.content.rfind("}") + 1
                    json_str = self.content[start:end]
                    json_obj = json.loads(json_str)
                    
                    # 格式化显示
                    result = json_obj.get("result", "")
                    reason = json_obj.get("reason", "")
                    
                    if result:
                        icon = Icons.SUCCESS if result == "是" else (Icons.ERROR if result in ["否", "错误"] else Icons.WARNING)
                        display_content = f"[bold]结果:[/bold] {icon} {result}\n\n[bold]原因:[/bold] {reason}"
            except Exception:
                pass
                
            self.panel.renderable = display_content
            self.live.refresh()
            
    def stop(self):
        """停止显示"""
        if self.live:
            self.live.stop()
            self.live = None
