# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目概述

多AI供应商客服问答语义比对工具，支持Gemini、OpenAI、Anthropic、Dify、iFlow五大供应商，通过标准化API接口评估AI客服回答与源知识库文档的语义相符性。当前版本v2.5+采用模块化架构，100%类型安全，企业级生产就绪。

## 常用命令

### 环境管理
```bash
# 使用 UV (推荐)
uv sync                           # 安装所有依赖
uv run python main.py            # 运行主程序
uv run python -m semantic_tester # 模块方式运行

# 使用 pip
pip install -r requirements.txt
python main.py

# 开发依赖安装
uv add --group dev black flake8 pytest
```

### 开发工具
```bash
# 代码格式化 (Black 标准，行长度88)
uv run black semantic_tester/

# 代码质量检查
uv run flake8 semantic_tester/ --max-line-length=120 --ignore=E203,W503,E501

# 语法验证
python3 -m py_compile semantic_tester/**/*.py
```

### 测试与构建
```bash
# 运行测试
uv run pytest

# 运行特定测试
uv run pytest tests/test_api.py -v

# 构建包
uv build

# 类型检查
mypy semantic_tester/ --ignore-missing-imports
```

### 日志查看
```bash
tail -f logs/semantic_test.log
```

## 模块化架构

### 核心层次结构
```
main.py (应用入口) → semantic_tester/ (核心包)
├── api/         # API接口层 - 多供应商抽象和统一接口
├── excel/       # 数据处理层 - Excel文件操作和结果保存
├── ui/          # 用户界面层 - CLI和交互式菜单
├── config/      # 配置管理层 - 环境变量和用户设置
└── utils/       # 工具函数层 - 文件、日志、验证等通用工具
```

### 多供应商架构模式

**抽象基类模式**: `AIProvider` 定义统一接口，所有供应商必须实现：
- `get_models()`: 获取可用模型列表
- `validate_api_key()`: API密钥验证
- `check_semantic_similarity()`: 核心语义比对功能
- `is_configured()`: 配置状态检查

**供应商管理器**: `ProviderManager` 统一管理5大AI供应商：
- Gemini: 多密钥轮转，429错误处理，智能冷却
- OpenAI: 标准API接口，GPT模型支持
- Anthropic: Claude API集成，最新模型支持
- Dify: 聊天客户端测试工具专用，私有化部署支持
- iFlow: 国产AI厂商，千问、月之暗面、智谱等

**配置一致性**: 所有供应商通过 `base_provider.py` 实现统一的错误处理、日志记录、等待提示机制。

### 关键设计模式

**多供应商轮转机制**:
- Gemini: `GeminiAPIHandler` 实现多密钥轮转和429错误自动重试，每个密钥独立冷却计时
- 其他供应商: 统一的重试机制和错误处理

**Excel处理器**: `ExcelProcessor` 支持增量保存，每条记录处理完立即写入Excel，防止数据丢失。

**配置管理**: `EnvManager` 处理环境变量验证，`Config` 处理用户设置持久化。

**格式检测**: 自动识别Dify Chat Tester输出格式，动态适配列映射。

**模板值过滤**: 配置文件中使用模板值(如 "your-api-key")会被识别为"未配置"状态，避免用户误用。

### 数据流处理

1. **初始化**: 环境变量验证 → API密钥有效性检查 → 日志系统设置
2. **文件处理**: Excel加载 → 格式检测 → 列映射配置 → 知识库文档匹配
3. **语义分析**: 逐行处理 → 文档内容读取 → AI供应商API调用 → 结果实时保存
4. **错误处理**: 完善的异常捕获 → 详细日志记录 → 用户友好错误提示

### 供应商模型规范

**模型命名约定**:
- Gemini: `gemini-2.5-flash`, `gemini-2.5-pro` (无"models/"前缀)
- OpenAI: `gpt-4o`, `gpt-4o-mini`, `o1-preview`, `o1-mini`
- Anthropic: `claude-sonnet-4-20250514`, `claude-3-5-sonnet-20241022`
- iFlow: `qwen3-max`, `kimi-k2-0905`, `glm-4.6`, `deepseek-v3.2`

**环境变量标准化**:
- Gemini: `GEMINI_API_KEY` (多密钥用逗号分隔)
- OpenAI: `OPENAI_API_KEY`
- Anthropic: `ANTHROPIC_API_KEY`
- Dify: `DIFY_API_KEY`, `DIFY_BASE_URL`, `DIFY_APP_ID`
- iFlow: `IFLOW_API_KEY`, `IFLOW_BASE_URL`

## 环境配置

### 必需环境变量
至少需要配置一个供应商的API密钥：
```bash
# Gemini (支持多密钥轮转)
export GEMINI_API_KEY='KEY1,KEY2,KEY3'

# 或其他供应商
export OPENAI_API_KEY='sk-your-key'
export ANTHROPIC_API_KEY='sk-ant-your-key'
export DIFY_API_KEY='app-your-key'
export IFLOW_API_KEY='sk-your-key'
```

### 模型配置
每个供应商都有对应的模型环境变量：
```bash
export GEMINI_MODEL='gemini-2.5-flash'      # 默认模型
export OPENAI_MODEL='gpt-4o'
export ANTHROPIC_MODEL='claude-sonnet-4-20250514'
export IFLOW_MODEL='qwen3-max'
```

### 配置文件优先级
1. `.env` 文件 (推荐)
2. 环境变量
3. 交互式配置 (临时)

## Excel数据格式

### 输入要求 (列名可配置)
- **文档名称**: 知识库文件名 (如: `产品手册.md`)
- **问题点**: 用户提问内容
- **AI客服回答**: AI生成的回答内容

### 输出结果 (自动添加)
- **语义是否与源文档相符**: "是"/"否"/错误状态
- **判断依据**: Gemini API返回的详细判断理由

### Dify格式支持
自动检测并适配Dify Chat Tester输出：
- `原始问题` → `问题点`
- `{供应商名称}响应` → `AI客服回答`
- 自动添加`文档名称`列

## 代码质量标准

### 类型安全
- 100%类型注解覆盖，所有Pylance警告已修复
- 使用现代Python类型系统 (Optional, Union, Dict[str, Any]等)

### 代码风格
- Black格式化标准 (line-length=88)
- Flake8质量检查通过
- 函数文档字符串完整

### 架构原则
- 单一职责：每个模块专注特定功能领域
- 依赖注入：通过构造函数传递依赖
- 错误处理：分层异常处理，不向用户暴露技术细节

## 开发注意事项

- 所有代码修改必须保持类型注解完整
- 新功能需要添加相应的错误处理和日志记录
- Excel操作使用`processor.py`中的安全方法，支持合并单元格
- API调用使用对应供应商的处理机制，避免速率限制
- 配置变更通过`config/`模块管理，支持持久化存储
- 添加新供应商时继承`AIProvider`基类，实现所有抽象方法
- 模型名称必须符合各供应商的官方规范，注意格式差异

## API供应商接口规范

### 实现新供应商
新增AI供应商需要创建对应的Provider类并继承`AIProvider`:

```python
from .base_provider import AIProvider

class CustomProvider(AIProvider):
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.api_key = config.get("api_key", "")
        # 其他供应商特定配置

    def get_models(self) -> List[str]:
        return ["model-1", "model-2", "latest"]

    def validate_api_key(self, api_key: str) -> bool:
        # 实现API密钥验证逻辑
        pass

    def check_semantic_similarity(self, question: str, ai_answer: str,
                                source_document: str, model: Optional[str] = None) -> tuple[str, str]:
        # 实现核心语义比对逻辑
        pass

    def is_configured(self) -> bool:
        return bool(self.api_key and self.api_key != "your-api-key")
```

### 供应商集成
1. 在`provider_manager.py`的`_create_provider`方法中添加新的供应商创建逻辑
2. 在`env_loader.py`中添加默认配置和模板值检测
3. 更新`.env.config.example`配置模板
4. 在`pyproject.toml`中添加所需依赖

## 调试与故障排除

### 常见问题诊断

**供应商配置检查**:
```bash
# 运行供应商状态检查
uv run python -c "
from semantic_tester.api.provider_manager import ProviderManager
from semantic_tester.config.env_loader import EnvLoader
env = EnvLoader()
manager = ProviderManager(env.get_config())
manager.print_provider_status()
"
```

**API密钥验证**:
```bash
# 测试Gemini API连接
uv run python -c "
from semantic_tester.api.gemini_provider import GeminiProvider
provider = GeminiProvider({'api_keys': ['your-key'], 'model': 'gemini-2.5-flash'})
print(provider.test_connection())
"
```

**依赖检查**:
```bash
# 检查所有必需依赖
uv run python -c "
import google.genai, openai, anthropic, requests, pandas
print('所有依赖已正确安装')
"
```

### 日志分析
- API调用失败: 查看 `logs/semantic_test.log` 中的错误详情
- 配置问题: 程序启动时会显示详细的配置状态
- 性能问题: 日志中包含每个API调用的响应时间