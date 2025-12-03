"""
统一的提示词定义

注意：提示词现在可以通过 .env.config 文件配置
"""

# 默认语义检查提示词（当配置文件中没有配置时使用）
SEMANTIC_CHECK_PROMPT = """请判断以下AI客服回答与源知识库文档内容在语义上是否相符。

判断标准：
1. 如果AI客服回答的内容能够从源知识库文档中推断出来，或者与源文档的核心信息一致，则认为"相符"。
2. 如果AI客服回答的内容与源文档相悖，或者包含源文档中没有的信息且无法合理推断，则认为"不相符"。
3. 如果无法获取源文档内容或遇到技术性错误，则标记为"错误"。
4. 如果信息不足以做出明确判断，则标记为"不确定"。

**重要：result 字段必须严格使用以下四种值之一，不得使用其他任何值：**
- "是" - 表示AI回答与源文档语义相符
- "否" - 表示AI回答与源文档语义不符
- "错误" - 表示遇到技术性错误（如获取文档失败）
- "不确定" - 表示信息不足，无法明确判断

请严格按照以下JSON格式返回结果：
{{
    "result": "是" 或 "否" 或 "错误" 或 "不确定",
    "reason": "详细的判断依据，说明为什么是相符或不相符，请引用源文档内容作为佐证"
}}

问题点：
{question}

AI客服回答：
{ai_answer}

源知识库文档内容：
---
{source_document}
---

请直接返回JSON格式结果，不要包含其他内容。记住：result 字段只能是这四个值之一："是"、"否"、"错误"、"不确定"。"""


def get_semantic_check_prompt(env_manager=None) -> str:
    """
    获取语义检查提示词

    Args:
        env_manager: 环境管理器实例（可选）

    Returns:
        str: 语义检查提示词
    """
    if env_manager and hasattr(env_manager, "get_semantic_check_prompt"):
        return env_manager.get_semantic_check_prompt()
    return SEMANTIC_CHECK_PROMPT
