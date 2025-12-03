# AI 提示词自定义配置说明

## 概述

semantic_tester 项目现在支持通过配置文件自定义 AI 语义检查提示词,无需修改代码即可调整 AI 判断行为。

## 配置语义检查提示词

在 `.env.config` 文件中添加或修改 `SEMANTIC_CHECK_PROMPT` 配置项。

### 支持的占位符

- `{question}`: 问题内容
- `{ai_answer}`: AI 的回答内容
- `{source_document}`: 源知识库文档内容

## 使用示例

### 1. 更严格的判断标准

```ini
SEMANTIC_CHECK_PROMPT=你是一个严格的质量检查员。请非常严格地判断AI回答是否与源文档完全一致。
只有当AI回答的每一个细节都能在源文档中找到直接依据时，才能判定为"是"。
如果有任何推断或延伸，都应该判定为"否"。

问题点：{question}
AI客服回答：{ai_answer}
源知识库文档内容：{source_document}

返回JSON格式：{{"result": "是/否/错误/不确定", "reason": "判断理由"}}
```

### 2. 更宽松的判断标准

```ini
SEMANTIC_CHECK_PROMPT=你是一个友好的质量审核员。请判断AI回答是否与源文档的核心意思一致。
只要AI回答没有明显错误，且大致符合源文档的主旨，就可以判定为"是"。

问题：{question}
回答：{ai_answer}
源文档：{source_document}

返回JSON：{{"result": "是/否/错误/不确定", "reason": "理由"}}
```

### 3. 英文提示词

```ini
SEMANTIC_CHECK_PROMPT=Please determine if the AI customer service answer is semantically consistent with the source knowledge base document.

Question: {question}
AI Answer: {ai_answer}
Source Document: {source_document}

Return JSON: {{"result": "yes/no/error/uncertain", "reason": "explanation"}}
```

## 配置优先级

1. **环境变量** `SEMANTIC_CHECK_PROMPT`: 最高优先级
2. **.env.config 文件**: 项目配置文件
3. **默认值**: 内置默认提示词

## 测试配置

```bash
# 测试提示词是否正确加载
uv run python -c "from semantic_tester.config.environment import EnvManager; env = EnvManager(); print(f'Prompt length: {len(env.get_semantic_check_prompt())} chars')"
```

## 注意事项

1. **占位符必须保留**: `{question}`, `{ai_answer}`, `{source_document}` 必须在提示词中
2. **重启生效**: 修改配置后需要重启程序
3. **恢复默认**: 删除或注释掉配置项即可恢复默认提示词
