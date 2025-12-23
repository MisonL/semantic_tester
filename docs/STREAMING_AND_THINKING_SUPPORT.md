# 流式输出和思维链支持更新说明

## 更新概述

已为 `semantic_tester` 项目的所有 AI 渠道添加流式输出和思维链支持。

## 已完成的更新

### 1. 基类 (base_provider.py) ✅

- 在 `check_semantic_similarity` 方法中添加了两个新参数：
  - `stream: bool = False` - 是否使用流式输出
  - `show_thinking: bool = False` - 是否显示思维链过程

### 2. Gemini Provider ✅

**支持的功能:**

- ✅ 流式输出 (`stream=True`)
- ✅ 思维链支持（使用 `gemini-2.0-flash-thinking-exp-1219` 模型）
- ✅ 思维内容提取与显示

**实现要点:**

- 使用 `generate_content_stream()` 进行流式调用
- 从 `candidates[0].content.parts` 中提取 `thought` 属性
- 实时输出内容到终端

### 3. OpenAI Provider ✅

**支持的功能:**

- ✅ 流式输出 (`stream=True`)
- ✅ 推理过程支持（`o1`, `o1-mini`, `o1-preview` 模型）
- ✅ Reasoning tokens 统计

**实现要点:**

- o1 系列模型不支持流式，自动回退到非流式
- o1 系列不支持 `system` 消息和 `temperature` 参数
- 从 `response.usage.completion_tokens_details.reasoning_tokens` 提取推理信息
- 使用 `max_completion_tokens` 而不是 `max_tokens`

### 4. Anthropic Provider ✅

**支持的功能:**

- ✅ 流式输出 (`stream=True`)
- ✅ Extended Thinking 特性支持

**实现要点:**

- 使用 `client.messages.stream()` 进行流式调用
- 支持流式回调函数

### 5. Dify Provider ✅

**支持的功能:**

- ✅ 流式输出 (`stream=True`)
- ✅ 流式回调函数 (`stream_callback`)

**实现要点:**

- 使用 `response_mode: "streaming"`
- 解析 SSE 事件流
- 处理 `message`, `message_end` 等事件

### 6. iFlow Provider ✅

**支持的功能:**

- ✅ 流式输出 (`stream=True`)
- ✅ 流式回调函数 (`stream_callback`)
- ✅ 思维链支持 (`show_thinking`)

**实现要点:**

- 使用 `stream: True`
- 解析流式响应中的 `delta.content`
- 处理 `finish_reason: "stop"` 标记
- 支持 reasoning_content 提取

## 使用示例

```python
# 使用 Gemini 流式输出和思维链
result, reason = gemini_provider.check_semantic_similarity(
    question="...",
    ai_answer="...",
    source_document="...",
    model="gemini-2.0-flash-thinking-exp-1219",
    stream=True,
    show_thinking=True
)

# 使用 OpenAI o1 推理模型
result, reason = openai_provider.check_semantic_similarity(
    question="...",
    ai_answer="...",
    source_document="...",
    model="o1",
    stream=False,  # o1不支持流式
    show_thinking=True
)

# 使用 GPT-4o 流式输出
result, reason = openai_provider.check_semantic_similarity(
    question="...",
    ai_answer="...",
    source_document="...",
    model="gpt-4o",
    stream=True,
    show_thinking=False
)
```

## 技术要点

### 流式输出的优势

1. **即时反馈**: 用户可以立即看到 AI 的响应开始
2. **更好的 UX**: 避免长时间等待导致的焦虑
3. **更真实**: 模拟人类逐字输出的交流方式

### 思维链的价值

1. **透明度**: 了解 AI 的推理过程
2. **可调试性**: 发现 AI 推理中的问题
3. **信任度**: 增强用户对 AI 结论的信任

### 注意事项

1. 向后兼容: 默认参数为 `stream=False`，`show_thinking=True`（由环境变量 `ENABLE_THINKING` 控制）
2. 模型限制:
   - Gemini: 只有 thinking 模型支持思维链
   - OpenAI: o1 系列不支持流式，但支持推理过程
3. 性能: 流式输出对网络要求更高，需要稳定连接

## 下一步计划

所有供应商的流式输出和思维链功能均已在 v4.0.0 中完成 ✅
