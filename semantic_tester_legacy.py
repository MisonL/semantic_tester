"""
作者：Mison
邮箱：1360962086@qq.com
仓库：https://github.com/MisonL/semantic_tester
许可证：MIT

AI客服问答语义比对工具

**建议与 [Dify 聊天客户端测试工具](https://github.com/MisonL/dify_chat_tester) 项目搭配使用，以实现Dify应用问答效果的自动化评估。**
本工具用于评估AI客服回答与源知识库文档内容在语义上是否相符。
它通过调用Google Gemini API，对给定的问题、AI客服回答和源文档内容进行比对，
判断AI客服的回答是否能够从源文档中合理推断，或是否与源文档的核心信息一致。

主要特性：
- 多API密钥自动轮转与冷却处理
- 速率限制(429错误)自动重试机制
- 实时保存处理进度（每条记录完成后立即保存）
- 灵活的列名配置支持
- 详细的运行日志记录

如何配置和使用：

1.  **获取 Gemini API 密钥：**
    *   访问 Google AI Studio (https://aistudio.google.com/app/apikey)
    *   创建或获取您的 Gemini API 密钥

2.  **设置环境变量：**
    *   配置API密钥到 `GEMINI_API_KEYS` 环境变量
    *   支持多个密钥（逗号/空格分隔）：
        `export GEMINI_API_KEYS='密钥1,密钥2,密钥3'`
    *   （可选）指定模型版本：
        `export GEMINI_MODEL='models/gemini-2.5-flash'`

3.  **准备 Excel 文件：**
    *   创建Excel文件（例如 `问答测试用例.xlsx`）
    *   必须包含以下列（名称可配置）：
        - `文档名称`：知识库文件名（如 `产品手册.md`)
        - `问题点`：用户提问内容
        - `AI客服回答`：AI生成的回答

4.  **准备知识库文档：**
    *   将Markdown文档放置在 `处理后/` 目录
    *   文件名需与Excel中`文档名称`列的值匹配
    *   目录结构示例：
        处理后/
          产品手册.md
          常见问题.md

5.  **运行程序：**
    *   安装依赖：`pip install -r requirements.txt`
    *   运行：`python semantic_tester.py`
    *   按提示配置Excel列映射

6.  **查看结果：**
    *   结果实时保存到Excel（`语义是否与源文档相符` 和 `判断依据`列）
    *   详细日志查看：`logs/semantic_test.log`

注意事项：
-   确保Gemini API密钥有效且已启用服务
-   保持网络连接正常
-   Excel文件需要正确格式
-   知识库文档需放在 `处理后/` 目录
-   程序会自动创建日志目录 `logs/`
"""

import pandas as pd
from google import genai
from google.genai import types
import os
import json
import logging
import time
import re
import sys
import google.api_core.exceptions  # 导入用于处理API异常的模块
from typing import List, Dict
from dotenv import load_dotenv  # 导入load_dotenv
import threading
from colorama import Fore, Style, init  # 导入colorama库，用于终端颜色输出
from openpyxl.cell.cell import MergedCell  # 导入用于处理合并单元格的类

# 初始化colorama，使其在不同终端下都能正常显示颜色
init()


# 添加等待指示器功能
def show_waiting_indicator(stop_event, prefix="Gemini"):
    """显示等待状态指示器"""
    indicators = ["⣾", "⣽", "⣻", "⢿", "⡿", "⣟", "⣯", "⣷"]
    idx = 0
    while not stop_event.is_set():
        sys.stdout.write(f"\r{prefix}: 正在思考 {indicators[idx]} ")
        sys.stdout.flush()
        idx = (idx + 1) % len(indicators)
        time.sleep(0.1)
    # 清除等待指示器
    sys.stdout.write("\r" + " " * 30 + "\r")
    sys.stdout.flush()


def write_cell_safely(worksheet, row, col, value):
    """
    安全地写入 Excel 单元格，处理合并单元格的情况。
    如果目标单元格是合并单元格的一部分，则写入合并区域的左上角单元格。
    """
    cell_obj = worksheet.cell(row=row, column=col)
    if isinstance(cell_obj, MergedCell):
        # 如果是合并单元格的一部分，找到其合并区域的左上角单元格
        for merged_range in worksheet.merged_cells.ranges:
            if cell_obj.coordinate in merged_range:
                min_col, min_row, max_col, max_row = merged_range.bounds
                worksheet.cell(row=min_row, column=min_col).value = value
                return
    else:
        cell_obj.value = value


# 辅助函数：获取列索引
def get_column_index(column_names: List[str], col_input: str) -> int:
    try:
        col_num = int(col_input)
        if 1 <= col_num <= len(column_names):
            return col_num - 1
        else:
            return -1  # 无效序号
    except ValueError:
        try:
            return column_names.index(col_input)
        except ValueError:
            return -1  # 未找到列名


# 辅助函数：获取或新增列
def get_or_add_column(df: pd.DataFrame, column_names: List[str], col_input: str) -> int:
    try:
        col_num = int(col_input)
        if 1 <= col_num <= len(column_names):
            return col_num - 1
        else:
            # 如果是无效序号，但用户可能想新增一个名为数字的列
            new_col_name = col_input
            df[new_col_name] = pd.Series(dtype="object")
            column_names.append(new_col_name)
            logger.info(f"已新增列: '{new_col_name}'")
            return len(column_names) - 1
    except ValueError:
        if col_input in column_names:
            return column_names.index(col_input)
        else:
            # 新增列
            df[col_input] = pd.Series(dtype="object")
            column_names.append(col_input)
            logger.info(f"已新增列: '{col_input}'")
            return len(column_names) - 1


# 加载环境变量
load_dotenv()

# 配置日志
# 创建日志目录
log_dir = "logs"
if not os.path.exists(log_dir):
    os.makedirs(log_dir)

# 配置日志器，同时输出到文件和控制台
logging.basicConfig(
    level=logging.INFO,  # 默认日志级别
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(
            os.path.join(log_dir, "semantic_test.log"), encoding="utf-8"
        ),  # 输出到文件
        logging.StreamHandler(sys.stdout),  # 输出到控制台
    ],
)

logger = logging.getLogger(__name__)  # 使用logger实例

# 修改为加载多个API Key
GEMINI_API_KEYS_STR = os.getenv("GEMINI_API_KEYS")

GEMINI_API_KEYS = (
    [key.strip() for key in re.split(r"[\s,]+", GEMINI_API_KEYS_STR) if key.strip()]
    if GEMINI_API_KEYS_STR
    else []
)


# 定义Gemini API处理类
class GeminiAPIHandler:
    def __init__(self, api_keys: List[str], model_name: str, prompt_template: str):
        self.all_api_keys = api_keys  # 存储所有提供的API Key
        self.api_keys: List[str] = []  # 存储经过有效性测试后的可用API Key
        self.current_key_index = 0
        self.model_name = model_name
        self.prompt_template = prompt_template
        self.client = None  # 使用client替代model
        # 存储每个API Key上次使用的时间戳，用于轮转判断
        self.key_last_used_time: Dict[str, float] = {}
        # 存储每个API Key的冷却结束时间（429错误后）
        self.key_cooldown_until: Dict[str, float] = {}
        self.first_actual_call = True  # 新增标志，用于判断是否是首次实际API调用

        self._initialize_api_keys()  # 初始化时进行API Key有效性测试
        self._configure_gemini_api()  # 配置Gemini API

    def _initialize_api_keys(self):
        """测试并初始化可用的API Key列表。初始化时不触发等待。"""
        logger.info("开始测试Gemini API Key的有效性...")
        valid_keys = []
        current_time = time.time()
        for key in self.all_api_keys:
            # 初始化测试时不触发等待
            if self._test_api_key_validity(key, during_initialization=True):
                valid_keys.append(key)
                # 初始化时记录当前时间，避免首次使用时显示大数值
                self.key_last_used_time[key] = current_time
                self.key_cooldown_until[key] = 0.0

        self.api_keys = valid_keys
        if not self.api_keys:
            logger.critical(
                "所有提供的Gemini API Key均无效或未设置。语义比对功能将无法使用。"
            )
        else:
            logger.info(f"成功识别 {len(self.api_keys)} 个有效Gemini API Key。")

    def _test_api_key_validity(
        self, api_key: str, during_initialization: bool = False
    ) -> bool:
        """
        测试单个Gemini API Key的有效性。
        通过尝试获取模型信息来验证，不列出所有模型。
        Args:
            api_key (str): 要测试的API Key。
            during_initialization (bool): 是否在初始化阶段调用此方法。
        """
        if not re.match(r"^[a-zA-Z0-9_-]{20,}$", api_key):
            logger.warning(f"API Key格式无效: {api_key[:5]}...。")
            return False

        try:
            # 使用新SDK创建客户端
            client = genai.Client(api_key=api_key)

            # 尝试获取特定模型信息（轻量级验证）
            # 使用一个已知模型名称，例如"gemini-2.5-flash"
            model_info = client.models.get(model="models/gemini-2.5-flash")
            if model_info:
                # 初始化阶段只记录有效性，不触发等待日志
                if not during_initialization:
                    logger.info(f"API Key {api_key[:5]}... 有效。")
                return True
            return False
        except Exception:  # 异常信息有意不使用，仅表示验证失败
            # 初始化阶段只记录警告，不触发等待日志
            if not during_initialization:
                logger.warning(f"API Key {api_key[:5]}... 为无效或已过期。请检查：")
                logger.info(
                    "1. API密钥是否正确（在 https://aistudio.google.com/app/apikey 查看）"
                )
                logger.info("2. 网络连接是否正常（特别是代理设置）")
                logger.info(
                    "3. 是否启用了Gemini API（在 https://console.cloud.google.com/apis/api/generativelanguage.googleapis.com/ 启用）"
                )
            return False

    def _configure_gemini_api(self):
        """配置Gemini API，使用当前API Key。"""
        if not self.api_keys:
            logger.warning("没有可用的Gemini API密钥，无法配置模型。")
            self.client = None  # 确保客户端为None
            return

        current_api_key = self.api_keys[self.current_key_index]
        try:
            # 使用新SDK创建客户端
            self.client = genai.Client(api_key=current_api_key)
            logger.info(
                f"Gemini API 已配置，使用密钥索引: {self.current_key_index} (密钥: {current_api_key[:5]}...)，模型: {self.model_name}"
            )
            # 成功配置后，更新当前key的上次使用时间
            self.key_last_used_time[current_api_key] = time.time()
        except Exception as e:
            logger.error(f"Gemini API 配置失败，密钥索引 {self.current_key_index}: {e}")
            logger.info("请检查：")
            logger.info(
                "1. API密钥是否正确（在 https://aistudio.google.com/app/apikey 查看）"
            )
            logger.info("2. 网络连接是否正常（特别是代理设置）")
            logger.info(
                "3. 是否启用了Gemini API（在 https://console.cloud.google.com/apis/api/generativelanguage.googleapis.com/ 启用）"
            )
            self.client = None
            # 如果当前密钥配置失败，尝试轮转到下一个密钥
            if self.api_keys:  # 只有当还有其他密钥时才尝试轮转
                logger.info("当前密钥配置失败，尝试轮转到下一个可用密钥。")
                self.rotate_key(force_rotate=True)  # 强制轮转到下一个密钥

    def rotate_key(self, force_rotate: bool = False):
        """
        轮转到下一个API Key。
        Args:
            force_rotate (bool): 如果为True，则强制轮转，跳过冷却时间检查。
        """
        if not self.api_keys:
            logger.warning("没有可用的API密钥进行轮转。")
            return

        current_time = time.time()

        # 调试日志：显示所有密钥状态
        logger.debug(
            f"开始密钥轮转，当前密钥索引: {self.current_key_index}, 强制轮转: {force_rotate}"
        )
        for index, key in enumerate(self.api_keys):
            cooldown_until = self.key_cooldown_until.get(key, 0.0)
            cooldown_remaining = max(0.0, cooldown_until - current_time)
            time_since_last_use = current_time - self.key_last_used_time.get(key, 0.0)
            logger.debug(
                f"密钥 {index}: 冷却剩余 {cooldown_remaining:.1f}s, 上次使用 {time_since_last_use:.1f}s前"
            )

        # 循环直到找到一个可用的密钥
        for _ in range(len(self.api_keys)):
            self.current_key_index = (self.current_key_index + 1) % len(self.api_keys)
            next_key = self.api_keys[self.current_key_index]

            cooldown_until = self.key_cooldown_until.get(next_key, 0.0)
            cooldown_remaining = max(0.0, cooldown_until - current_time)
            time_since_last_use = current_time - self.key_last_used_time.get(
                next_key, 0.0
            )

            # 强制轮转（因429错误）直接使用下一个密钥
            if force_rotate:
                logger.info(
                    f"强制轮转: 跳过等待, 新密钥索引: {self.current_key_index} (密钥: {next_key[:5]}...)"
                )
                self.key_last_used_time[next_key] = current_time
                self._configure_gemini_api()
                return

            # 检查密钥是否可用
            if cooldown_remaining <= 0:
                # 如果是首次实际调用，则跳过60秒等待
                if self.first_actual_call:
                    logger.info(
                        f"首次实际调用，密钥 {self.current_key_index} 可用 (密钥: {next_key[:5]}...)"
                    )
                    self.first_actual_call = False  # 标记首次调用已完成
                # 智能等待策略：距离上次使用不足60秒则等待
                elif time_since_last_use < 60:
                    wait_time = 60 - time_since_last_use
                    logger.info(
                        f"密钥 {self.current_key_index} 需要等待: {wait_time:.1f}s (上次使用: {time_since_last_use:.1f}s前)"
                    )
                    # 在这里添加等待提示
                    stop_event = threading.Event()
                    waiting_thread = threading.Thread(
                        target=show_waiting_indicator, args=(stop_event, "等待密钥冷却")
                    )
                    waiting_thread.daemon = True
                    waiting_thread.start()
                    time.sleep(wait_time)
                    stop_event.set()
                    if waiting_thread.is_alive():
                        waiting_thread.join(timeout=0.5)

                logger.info(
                    f"密钥 {self.current_key_index} 可用 (冷却已过, 密钥: {next_key[:5]}...)"
                )
                self.key_last_used_time[next_key] = time.time()  # 更新为当前时间
                self._configure_gemini_api()
                return
            else:
                logger.info(
                    f"密钥 {self.current_key_index} 冷却中: 剩余 {cooldown_remaining:.1f}s (密钥: {next_key[:5]}...)"
                )

        # 所有密钥都不可用时等待最长冷却时间
        max_cooldown = max(self.key_cooldown_until.values(), default=0) - current_time
        if max_cooldown > 0:
            logger.warning(f"所有密钥不可用，等待最长冷却时间: {max_cooldown:.1f}s")
            # 在这里添加等待提示
            stop_event = threading.Event()
            waiting_thread = threading.Thread(
                target=show_waiting_indicator, args=(stop_event, "等待所有密钥冷却")
            )
            waiting_thread.daemon = True
            waiting_thread.start()
            time.sleep(max_cooldown)
            stop_event.set()
            if waiting_thread.is_alive():
                waiting_thread.join(timeout=0.5)

            self.rotate_key(force_rotate)  # 递归尝试
        else:
            logger.error("所有密钥均不可用且无有效冷却时间")
            # 在所有密钥都不可用时，不退出程序，而是让调用者处理无可用模型的情况
            self.client = None  # 确保客户端为None

    def get_client(self):
        """获取当前配置的Gemini客户端实例。"""
        return self.client

    def get_prompt(
        self, question: str, ai_answer: str, source_document_content: str
    ) -> str:
        """生成带问答和源文档内容的提示词。"""
        # semantic_tester.py 的提示词逻辑不同，直接在这里构建
        return f"""
请判断以下AI客服回答与源知识库文档内容在语义上是否相符。
如果AI客服回答的内容能够从源知识库文档中推断出来，或者与源文档的核心信息一致，则认为相符。
如果AI客服回答的内容与源文档相悖，或者包含源文档中没有的信息且无法合理推断，则认为不相符。

请以JSON格式返回结果，包含两个字段：
- "result": "是" 或 "否"
- "reason": 详细的判断依据

问题点: {question}
AI客服回答: {ai_answer}
源知识库文档内容:
---
{source_document_content}
---

请直接回答JSON。
"""


def check_semantic_similarity(
    gemini_api_handler: GeminiAPIHandler,
    question: str,
    ai_answer: str,
    source_document_content: str,
):
    """
    使用Gemini API判断AI客服回答与源文档在语义上是否相符，并返回判断结果和原因。
    使用GeminiAPIHandler处理API调用和密钥轮转。
    """
    response_text = ""  # 初始化response_text
    max_retries = 5  # API调用重试次数
    default_retry_delay = 60  # 默认等待时间（秒）

    for attempt in range(max_retries):
        start_time = time.time()  # 记录API调用开始时间

        # 在每次API调用前尝试轮转密钥并获取客户端
        gemini_api_handler.rotate_key()
        client = gemini_api_handler.get_client()

        if not client:
            logger.warning(
                f"Gemini客户端未成功初始化或无可用密钥，跳过API调用 (问题: '{question[:50]}...', 尝试 {attempt + 1}/{max_retries})。"
            )  # 增加问题点信息
            if attempt < max_retries - 1:
                # 如果没有可用密钥，等待一段时间再重试
                logger.info(
                    f"等待 {default_retry_delay} 秒后重试 (问题: '{question[:50]}...')。"
                )  # 增加问题点信息
                time.sleep(default_retry_delay)
                continue
            else:
                logger.error(
                    f"多次尝试后仍无可用Gemini模型，语义比对失败 (问题: '{question[:50]}...')。"
                )
                return "错误", "无可用Gemini模型"

        prompt = gemini_api_handler.get_prompt(
            question, ai_answer, source_document_content
        )

        # 创建停止事件和等待线程
        stop_event = threading.Event()
        waiting_thread = threading.Thread(
            target=show_waiting_indicator, args=(stop_event, "Gemini")
        )
        waiting_thread.daemon = True
        waiting_thread.start()

        try:
            try:
                logger.info(
                    f"正在调用Gemini API进行语义比对 (问题: '{question[:50]}...', 尝试 {attempt + 1}/{max_retries})..."
                )  # 增加问题点信息
                # 使用新SDK生成内容（使用正确的配置类型）
                response = client.models.generate_content(
                    model=gemini_api_handler.model_name,
                    contents=[prompt],
                    config=types.GenerateContentConfig(temperature=0),
                )
                end_time = time.time()  # 记录API调用结束时间
                duration = end_time - start_time  # 计算耗时
                logger.info(
                    f"Gemini API调用完成，耗时: {duration:.2f} 秒 (问题: '{question[:50]}...')。"
                )  # 增加问题点信息

                # 确保响应有效
                if response is None or response.text is None:
                    logger.warning("Gemini API返回空响应")
                    return "错误", "API返回空响应"

                # 尝试解析Gemini返回的JSON
                response_text = response.text.strip()
                # 移除可能存在的Markdown代码块标记
                if response_text.startswith("```json") and response_text.endswith(
                    "```"
                ):
                    response_text = response_text[7:-3].strip()

                try:
                    parsed_response = json.loads(response_text)
                    result = parsed_response.get("result", "无法判断").strip()
                    reason = parsed_response.get("reason", "无").strip()

                    # 根据结果设置颜色和加粗
                    colored_result = result
                    if result == "是":
                        colored_result = (
                            Style.BRIGHT + Fore.GREEN + result + Style.RESET_ALL
                        )
                    elif result == "否":
                        colored_result = (
                            Style.BRIGHT + Fore.RED + result + Style.RESET_ALL
                        )

                    logger.info(
                        f"语义比对结果：{colored_result} (问题: '{question[:50]}...')"
                    )  # 增加问题点信息
                    return result, reason
                except json.JSONDecodeError as e:
                    logger.warning(f"解析JSON失败: {response_text}, 错误: {e}")
                    return "错误", f"JSON解析失败: {e}"

            except json.JSONDecodeError as e:
                end_time = time.time()  # 记录API调用结束时间
                duration = end_time - start_time  # 计算耗时
                logger.warning(
                    f"Gemini返回的JSON格式不正确：{response_text}，错误：{e}，耗时: {duration:.2f} 秒 (问题: '{question[:50]}...')。"
                )  # 增加问题点信息
                # JSON解析错误通常不是临时错误，不进行重试
                return "错误", f"JSON解析错误: {e}"

            except google.api_core.exceptions.ResourceExhausted as e:
                end_time = time.time()  # 记录API调用结束时间
                duration = end_time - start_time  # 计算耗时
                error_msg = str(e)
                logger.warning(
                    f"调用Gemini API时发生速率限制错误 (429) (问题: '{question[:50]}...', 尝试 {attempt+1}/{max_retries})：{error_msg}，耗时: {duration:.2f} 秒"
                )  # 增加问题点信息

                retry_after = default_retry_delay
                # 尝试从异常对象本身或其details属性中提取retryDelay
                details = getattr(
                    e, "details", []
                )  # 尝试获取details属性，如果不存在则为空列表
                if not details and hasattr(
                    e, "message"
                ):  # 如果details为空，尝试解析错误消息字符串
                    # 尝试从错误消息字符串中解析retryDelay
                    retry_delay_match = re.search(r"'retryDelay': '(\d+)s'", error_msg)
                    if retry_delay_match:
                        try:
                            retry_after = (
                                int(retry_delay_match.group(1)) + 5
                            )  # 增加5秒缓冲
                            logger.info(
                                f"从错误消息中提取到建议的重试延迟: {retry_after} 秒 (问题: '{question[:50]}...')。"
                            )  # 增加问题点信息
                        except ValueError:
                            logger.warning(
                                f"无法解析错误消息中的retryDelay。使用默认等待时间 {default_retry_delay} 秒 (问题: '{question[:50]}...')。"
                            )  # 增加问题点信息
                            retry_after = default_retry_delay
                    else:
                        logger.warning(
                            f"未在错误详情或错误消息中找到retryDelay信息。使用默认等待时间 {default_retry_delay} 秒 (问题: '{question[:50]}...')。"
                        )  # 增加问题点信息
                        retry_after = default_retry_delay
                else:  # 如果details不为空，遍历details查找retryDelay
                    found_retry_delay = False
                    for detail in details:
                        # 假设detail是ErrorInfo对象或类似结构
                        if hasattr(detail, "retry_delay") and hasattr(
                            detail.retry_delay, "seconds"
                        ):
                            retry_after = detail.retry_delay.seconds
                            logger.info(
                                f"从API错误详情中提取到建议的重试延迟: {retry_after} 秒 (问题: '{question[:50]}...')。"
                            )  # 增加问题点信息
                            found_retry_delay = True
                            break
                    if not found_retry_delay:
                        logger.warning(
                            f"在错误详情中未找到retryDelay信息。使用默认等待时间 {default_retry_delay} 秒 (问题: '{question[:50]}...')。"
                        )  # 增加问题点信息
                        retry_after = default_retry_delay

                if attempt < max_retries - 1:
                    logger.info(
                        f"检测到429错误，立即强制轮转到下一个密钥 (问题: '{question[:50]}...')。"
                    )  # 增加问题点信息
                    # 更新当前密钥的冷却时间
                    current_key = gemini_api_handler.api_keys[
                        gemini_api_handler.current_key_index
                    ]
                    gemini_api_handler.key_cooldown_until[current_key] = (
                        time.time() + retry_after
                    )
                    gemini_api_handler.rotate_key(
                        force_rotate=True
                    )  # 强制轮转到下一个密钥
                    continue  # 重试当前记录
                else:
                    logger.error(
                        f"语义比对多次重试后失败 (问题: '{question[:50]}...'): {error_msg}"
                    )
                    return "错误", f"API调用多次重试失败: {error_msg}"

            except Exception as e:
                end_time = time.time()  # 记录API调用结束时间
                duration = end_time - start_time  # 计算耗时
                error_msg = str(e)
                logger.error(
                    f"调用Gemini API时发生错误 (问题: '{question[:50]}...', 尝试 {attempt+1}/{max_retries})：{error_msg}，耗时: {duration:.2f} 秒"
                )  # 增加问题点信息
                logger.debug(
                    f"完整错误信息: {str(e)}", exc_info=True
                )  # 添加详细错误日志

                # 非速率限制错误，也进行重试（可能是其他临时网络问题）
                if attempt < max_retries - 1:
                    logger.warning(
                        f"非速率限制错误，等待 {default_retry_delay} 秒后重试 (问题: '{question[:50]}...')。"
                    )  # 增加问题点信息
                    time.sleep(default_retry_delay)
                    # 强制轮转到下一个密钥并在下一次循环开始时使用
                    gemini_api_handler.rotate_key(force_rotate=True)
                    continue  # 重试当前记录
                else:
                    logger.error(
                        f"语义比对多次重试后失败 (问题: '{question[:50]}...'): {error_msg}"
                    )
                    return "错误", f"API调用多次重试失败: {error_msg}"

        finally:
            # 确保停止等待指示器
            stop_event.set()
            if waiting_thread.is_alive():
                waiting_thread.join(timeout=0.5)

    # 如果所有重试都失败
    return "错误", "API调用多次重试失败"


def main():
    # API Keys 已在文件顶部加载到 GEMINI_API_KEYS 列表中

    if not GEMINI_API_KEYS:
        logger.critical("错误：请设置 GEMINI_API_KEYS 环境变量。")
        logger.info("您可以通过以下命令设置（临时）：")
        logger.info("export GEMINI_API_KEYS='您的API密钥1,您的API密钥2'")
        logger.info("或者在您的.zshrc或.bashrc文件中设置（永久）。")
        sys.exit(1)  # 没有API密钥时退出程序

    # 初始化Gemini API处理器
    # 可以从环境变量或命令行参数获取模型名称和提示词，这里先硬编码
    # 实际应用中可以考虑使用argparse或环境变量
    gemini_model_name = os.getenv(
        "GEMINI_MODEL", "models/gemini-2.5-flash"
    )  # 默认模型名称
    # semantic_tester 的提示词是固定的，不需要从环境变量获取
    # gemini_prompt_template = os.getenv("PROMPT", "...") # semantic_tester 不需要可配置的提示词模板

    # semantic_tester 的提示词是固定的，直接在 GeminiAPIHandler 中构建
    gemini_api_handler = GeminiAPIHandler(
        api_keys=GEMINI_API_KEYS,
        model_name=gemini_model_name,
        prompt_template="",  # semantic_tester 的提示词在 get_prompt 方法中构建，这里可以为空
    )

    # 检查handler是否成功初始化（至少有一个有效密钥）
    if not gemini_api_handler.api_keys:
        logger.critical(
            "Gemini API Handler 初始化失败，没有可用的API密钥。程序将退出。"
        )
        sys.exit(1)

    print("\n--- AI客服问答语义比对工具 ---")

    # --- 获取 Excel 文件路径 ---
    excel_files = [
        f for f in os.listdir(".") if f.endswith(".xlsx") and os.path.isfile(f)
    ]
    while True:
        if excel_files:
            print("\n当前目录下的 Excel 文件:")
            for i, file_name in enumerate(excel_files):
                print(f"{i+1}. {file_name}")
            file_input = input("请输入 Excel 文件序号或直接输入文件路径: ")
            try:
                file_index = int(file_input)
                if 1 <= file_index <= len(excel_files):
                    excel_path = excel_files[file_index - 1]
                else:
                    print(
                        f"错误: 无效的文件序号 '{file_index}'。请重新输入。",
                        file=sys.stderr,
                    )
                    continue
            except ValueError:  # 用户输入的是路径
                excel_path = file_input
        else:
            excel_path = input(
                "当前目录下没有找到 Excel 文件。请输入包含问答内容的 Excel 文件路径: "
            )

        if not os.path.exists(excel_path):
            print(f"错误: 文件 '{excel_path}' 不存在。请重新输入。", file=sys.stderr)
            continue
        try:
            # 使用 pandas 读取 Excel 文件以获取 DataFrame，指定引擎
            try:
                df = pd.read_excel(excel_path, engine="openpyxl")
            except:
                df = pd.read_excel(excel_path, engine="xlrd")

            logger.info(f"正在读取Excel文件：{excel_path}")
            logger.info(f"Excel文件读取成功，共 {len(df)} 行 {len(df.columns)} 列。")
            logger.info(f"列名: {list(df.columns)}")
            break  # 成功读取文件，跳出循环
        except Exception as e:
            print(
                f"错误: 无法读取 Excel 文件 '{excel_path}'。请确保文件格式正确且未被占用。错误信息: {e}。请重新输入。",
                file=sys.stderr,
            )
            continue

    # --- 获取知识库目录路径 ---
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
        break

    # --- 智能格式检测和适配 ---
    column_names = [str(col) for col in df.columns]  # 获取所有列名并转换为字符串
    print("\nExcel 文件中的列名:")
    for i, col_name in enumerate(column_names):
        print(f"{i+1}. {col_name}")

    # 检测是否为 dify_chat_tester 输出格式
    # 检查必需的核心列
    has_question_col = any(
        col in column_names for col in ["原始问题", "用户输入", "问题"]
    )
    has_response_col = any(col.endswith("响应") for col in column_names)
    has_timestamp_col = any(col in column_names for col in ["时间戳", "Timestamp"])
    # 综合判断是否为dify格式
    is_dify_format = has_question_col and has_response_col and has_timestamp_col

    if is_dify_format:
        # 找到问题列和响应列
        question_col = None
        response_col = None

        # 确定问题列
        for col in ["原始问题", "用户输入", "问题"]:
            if col in column_names:
                question_col = col
                break

        # 确定响应列（以"响应"结尾的列）
        response_cols = []
        for col in column_names:
            if col.endswith("响应") and col != question_col:
                response_cols.append(col)

        # 如果有多个响应列，让用户选择
        if len(response_cols) > 1:
            print(
                f"\n{Fore.YELLOW}发现多个响应列，请选择要使用的一个：{Style.RESET_ALL}"
            )
            for i, col in enumerate(response_cols):
                print(f"  {i+1}. {col}")

            while True:
                choice = input(
                    f"请输入选择 (1-{len(response_cols)}, 默认: 1): "
                ).strip()
                if not choice:
                    choice = "1"

                try:
                    choice_idx = int(choice) - 1
                    if 0 <= choice_idx < len(response_cols):
                        response_col = response_cols[choice_idx]
                        break
                    else:
                        print(f"选择无效，请输入 1-{len(response_cols)} 之间的数字。")
                except ValueError:
                    print("请输入有效的数字。")
        elif len(response_cols) == 1:
            response_col = response_cols[0]
        else:
            print(f"{Fore.RED}❌ 未找到任何响应列！{Style.RESET_ALL}")
            is_dify_format = False

    if is_dify_format:
        print(f"\n{Fore.GREEN}✅ 检测到 Dify Chat Tester 输出格式！{Style.RESET_ALL}")
        print("将自动适配列映射关系：")
        print(f"  • {question_col} → 问题点")
        print(f"  • {response_col} → AI客服回答")
        print("  • 文档名称 → 需要手动指定")

        # 自动添加文档名称列
        if "文档名称" not in column_names:
            df.insert(0, "文档名称", "")  # 在第一列插入文档名称列
            column_names.insert(0, "文档名称")
            print(
                f"\n{Fore.YELLOW}📝 已自动添加'文档名称'列，请稍后手动填写对应的文档名。{Style.RESET_ALL}"
            )

        # 设置默认列映射
        doc_name_col_index = 0  # 文档名称列
        question_col_index = column_names.index(question_col)
        ai_answer_col_index = column_names.index(response_col)

        print("\n已配置列映射：")
        print(f"  • 文档名称: 列 {doc_name_col_index + 1} ('文档名称')")
        print(f"  • 问题点: 列 {question_col_index + 1} ('{question_col}')")
        print(f"  • AI客服回答: 列 {ai_answer_col_index + 1} ('{response_col}')")

        # 询问是否使用自动配置
        use_auto_config = input(
            f"\n{Fore.CYAN}是否使用此自动配置？(Y/n，默认: Y): {Style.RESET_ALL}"
        ).lower()
        if use_auto_config != "n":
            # 跳过手动列配置，直接设置结果保存列
            goto_result_columns = True
        else:
            goto_result_columns = False
    else:
        goto_result_columns = False

    if not goto_result_columns:
        # --- 获取"文档名称"列 ---
        doc_name_col_input = input(
            '请输入"文档名称"所在列的名称或序号 (例如: "文档名称" 或 "1"): '
        )
        doc_name_col_index = get_column_index(column_names, doc_name_col_input)
        if doc_name_col_index == -1:
            logger.error(
                f"错误: 未找到列名为 '{doc_name_col_input}' 的'文档名称'列。程序退出。"
            )
            sys.exit(1)

        # --- 获取"问题点"列 ---
        question_col_input = input(
            '请输入"问题点"所在列的名称或序号 (例如: "问题点" 或 "2"): '
        )
        question_col_index = get_column_index(column_names, question_col_input)
        if question_col_index == -1:
            logger.error(
                f"错误: 未找到列名为 '{question_col_input}' 的'问题点'列。程序退出。"
            )
            sys.exit(1)

        # --- 获取"AI客服回答"列 ---
        ai_answer_col_input = input(
            '请输入"AI客服回答"所在列的名称或序号 (例如: "AI客服回答" 或 "3"): '
        )
        ai_answer_col_index = get_column_index(column_names, ai_answer_col_input)
        if ai_answer_col_index == -1:
            logger.error(
                f"错误: 未找到列名为 '{ai_answer_col_input}' 的'AI客服回答'列。程序退出。"
            )
            sys.exit(1)

    # --- 获取“语义是否与源文档相符”结果保存列 ---
    print("\n请选择“语义是否与源文档相符”结果保存列:")
    print("现有列名:")
    for i, col_name in enumerate(column_names):
        print(f"{i+1}. {col_name}")
    similarity_result_col_input = (
        input(
            "请输入要保存结果的列名或序号 (例如: '语义是否与源文档相符' 或直接输入新列名，默认: '语义是否与源文档相符'): "
        )
        or "语义是否与源文档相符"
    )
    get_or_add_column(
        df, column_names, similarity_result_col_input
    )

    # --- 获取“判断依据”结果保存列 ---
    print("\n请选择“判断依据”结果保存列:")
    print("现有列名:")
    for i, col_name in enumerate(column_names):
        print(f"{i+1}. {col_name}")
    reason_col_input = (
        input(
            "请输入要保存结果的列名或序号 (例如: '判断依据' 或直接输入新列名，默认: '判断依据'): "
        )
        or "判断依据"
    )
    get_or_add_column(df, column_names, reason_col_input)

    # --- 询问是否在控制台显示每个问题的比对结果 ---
    display_result_choice = input(
        "是否在控制台显示每个问题的比对结果？ (y/N，默认: N): "
    ).lower()
    show_comparison_result = display_result_choice == "y"

    # 检查结果输出路径，如果用户没有指定，则使用默认值
    output_excel_path = input(
        f"请输入结果Excel文件的保存路径 (默认: {excel_path.replace('.xlsx', '_评估结果.xlsx')}): "
    ) or excel_path.replace(".xlsx", "_评估结果.xlsx")

    # 检查结果列是否存在，如果不存在则创建，并指定dtype为object
    if similarity_result_col_input not in df.columns:
        df[similarity_result_col_input] = pd.Series(dtype="object")
    if reason_col_input not in df.columns:
        df[reason_col_input] = pd.Series(dtype="object")

    # 强制转换列的dtype为object，确保能够存储字符串，解决FutureWarning
    df[similarity_result_col_input] = df[similarity_result_col_input].astype("object")
    df[reason_col_input] = df[reason_col_input].astype("object")

    total_records = len(df)
    logger.info(f"共需处理 {total_records} 条问答记录。")

    # 单线程顺序处理
    for row_index, (index, row) in enumerate(df.iterrows()):
        row_number = row_index + 1

        # 显示处理进度
        logger.info(f"正在处理第 {row_number}/{total_records} 条记录...")

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

        # 检查关键字段是否为空
        if not question or not ai_answer:
            logger.warning(
                f"跳过第 {row_number}/{total_records} 条记录：问题或AI客服回答为空。"
            )
            df.at[index, similarity_result_col_input] = "跳过"
            df.at[index, reason_col_input] = "问题或AI客服回答为空"
            # 每处理一条记录（包括跳过的）都检查是否需要保存中间结果
            try:
                df.to_excel(output_excel_path, index=False)
                logger.info(
                    f"已保存中间结果到 {output_excel_path} (已处理 {row_number} 条记录)。"
                )
            except Exception as e:
                logger.error(
                    f"保存中间结果到Excel文件时发生错误：{output_excel_path} - {e}"
                )
            continue  # 跳过当前记录

        logger.info(f"正在处理记录 (文档: {doc_name}, 问题: '{question[:50]}...')")

        md_file_path = os.path.join(knowledge_base_dir, doc_name)
        source_document_content = None

        if os.path.exists(md_file_path):
            try:
                with open(md_file_path, "r", encoding="utf-8") as f:
                    source_document_content = f.read()
            except Exception as e:
                df.at[index, similarity_result_col_input] = "读取源文档错误"
                df.at[index, reason_col_input] = f"读取Markdown文件时发生错误: {e}"
                logger.error(f"错误：读取Markdown文件时发生错误：{md_file_path} - {e}")
                # 每处理一条记录（包括错误的）都检查是否需要保存中间结果
                try:
                    df.to_excel(output_excel_path, index=False)
                    logger.info(
                        f"已保存中间结果到 {output_excel_path} (已处理 {row_number} 条记录)。"
                    )
                except Exception as e:
                    logger.error(
                        f"保存中间结果到Excel文件时发生错误：{output_excel_path} - {e}"
                    )
                continue  # 跳过当前记录

            # 调用语义比对函数
            similarity_result, reason = check_semantic_similarity(
                gemini_api_handler, question, ai_answer, source_document_content
            )

            # 更新DataFrame
            df.at[index, similarity_result_col_input] = similarity_result
            df.at[index, reason_col_input] = reason

            # 根据结果设置颜色和加粗
            if show_comparison_result:  # 根据用户选择是否显示
                colored_similarity_result = similarity_result
                if similarity_result == "是":
                    colored_similarity_result = (
                        Style.BRIGHT + Fore.GREEN + similarity_result + Style.RESET_ALL
                    )
                elif similarity_result == "否":
                    colored_similarity_result = (
                        Style.BRIGHT + Fore.RED + similarity_result + Style.RESET_ALL
                    )
                logger.info(
                    f"第 {row_number}/{total_records} 条记录处理完成。结果: {colored_similarity_result}"
                )

        else:
            df.at[index, similarity_result_col_input] = "源文档未找到"
            df.at[index, reason_col_input] = f"未找到对应的Markdown文件：{doc_name}"
            logger.warning(f"警告：未找到对应的Markdown文件：{md_file_path}")

        # 每处理完一条记录就保存结果
        try:
            df.to_excel(output_excel_path, index=False)
            logger.info(
                f"已保存结果到 {output_excel_path} (已处理 {row_number} 条记录)。"
            )
        except Exception as e:
            logger.error(f"保存结果到Excel文件时发生错误：{output_excel_path} - {e}")

    # 所有记录处理完成后，保存最终结果 (此处已在循环中每条保存，最终保存可省略或作为额外保险)
    # try:
    #     df.to_excel(output_excel_path, index=False)
    #     logger.info(f"所有 {total_records} 条记录处理完成，最终结果已保存到 {output_excel_path}。")
    # except Exception as e:
    #     logger.error(f"保存最终结果到Excel文件时发生错误：{output_excel_path} - {e}")


if __name__ == "__main__":
    main()
