# Project Context for iFlow CLI

## 项目概述

**AI客服问答语义比对工具** - 一个用于评估AI客服回答与源知识库文档内容在语义上是否相符的Python工具。

通过调用多个AI供应商API（Gemini、OpenAI、Dify、Anthropic、iFlow），对给定的问题、AI客服回答和源文档内容进行比对，判断AI客服的回答是否能够从源文档中合理推断，或是否与源文档的核心信息一致。

## 核心特性

### 🧠 多供应商智能语义比对
- **多AI供应商支持**: Gemini、OpenAI、Anthropic、Dify、iFlow
- 统一的语义分析接口，供应商间无缝切换
- 判断AI回答与知识库文档的语义一致性
- 输出标准化的比对结果和判断依据

### ⚙️ 多供应商API管理
- **统一供应商管理**: 支持同时配置多个AI供应商
- **智能密钥轮转**: Gemini多密钥自动轮转和冷却处理
- **容错机制**: 速率限制自动重试，供应商故障自动切换
- **灵活配置**: 支持.env文件、环境变量、交互式配置

### 📊 实时Excel处理
- **增量保存**: 每条记录处理后立即保存结果
- 灵活列名配置，支持自定义列
- 自动创建结果列（语义是否相符/判断依据）
- 合并单元格安全写入
- **Dify格式智能适配**: 自动识别Dify Chat Tester输出格式

### 🏗️ 模块化架构 (v2.0+)
- **清晰的模块分离**: API、Excel、UI、配置、工具模块独立
- **易于维护和扩展**: 每个模块职责单一，便于功能扩展
- **配置管理**: 支持配置文件持久化和用户自定义设置
- **多种运行模式**: 交互式菜单模式和命令行快速处理模式

### 🛡️ 类型安全 (v2.5+)
- **100% 类型安全**: 所有 Pylance 警告已修复
- **完善的类型注解**: 使用现代 Python 类型系统
- **静态检查通过**: 符合生产环境代码质量标准

## 技术栈

### 核心依赖
- **Python**: 3.9+
- **pandas**: Excel文件处理
- **openpyxl**: Excel读写支持
- **google-genai**: Gemini API客户端
- **openai**: OpenAI API客户端
- **anthropic**: Anthropic API客户端
- **requests**: HTTP请求库
- **python-dotenv**: 环境变量管理
- **colorama**: 终端彩色输出

### 开发工具
- **uv**: 现代Python包管理器（推荐）
- **pytest**: 测试框架
- **black**: 代码格式化
- **flake8**: 代码检查

## 项目架构

### 目录结构
```
semantic_tester/
├── __init__.py              # 包初始化
├── __main__.py              # 模块入口点
├── api/                     # API 接口层
│   ├── base_provider.py     # 供应商基类
│   ├── provider_manager.py  # 供应商管理器
│   ├── gemini_provider.py   # Gemini供应商实现
│   ├── openai_provider.py   # OpenAI供应商实现
│   ├── anthropic_provider.py # Anthropic供应商实现
│   ├── dify_provider.py     # Dify供应商实现
│   ├── iflow_provider.py    # iFlow供应商实现
│   └── gemini_handler.py    # 传统Gemini处理器（向后兼容）
├── config/                  # 配置管理层
│   ├── env_loader.py        # 环境变量加载器
│   ├── environment.py       # 环境管理器
│   └── settings.py          # 配置设置
├── excel/                   # Excel 处理层
│   ├── processor.py         # Excel数据处理
│   └── utils.py             # Excel工具函数
├── ui/                      # 用户界面层
│   ├── cli.py               # 命令行界面
│   └── menu.py              # 交互式菜单
└── utils/                   # 工具函数层
    ├── file_utils.py        # 文件操作工具
    ├── format_utils.py      # 格式化工具
    ├── logger_utils.py      # 日志工具
    └── validation_utils.py  # 验证工具
```

### 核心模块说明

#### 1. API模块 (`api/`)
- **ProviderManager**: 统一管理所有AI供应商，提供供应商选择、切换、状态监控
- **BaseProvider**: 抽象基类，定义统一的供应商接口
- **各供应商实现**: 封装不同AI供应商的API调用，提供统一的语义比对接口
- **GeminiHandler**: 传统的Gemini处理器，保持向后兼容

#### 2. 配置模块 (`config/`)
- **EnvLoader**: 从.env文件加载配置，支持自动创建默认配置
- **Environment**: 管理环境变量，提供API密钥、模型配置等
- **Settings**: 应用设置管理，支持用户自定义配置

#### 3. Excel模块 (`excel/`)
- **ExcelProcessor**: 核心Excel处理类，支持读写、格式检测、结果保存
- **Dify格式适配**: 自动识别Dify Chat Tester输出格式，智能列映射
- **增量保存**: 实时保存处理进度，防止数据丢失

#### 4. UI模块 (`ui/`)
- **CLIInterface**: 命令行交互界面，处理用户输入输出
- **MenuHandler**: 交互式菜单系统，提供友好的用户体验

#### 5. 工具模块 (`utils/`)
- **LoggerUtils**: 日志管理，支持文件和控制台输出
- **FileUtils**: 文件操作工具，支持文档查找和读取
- **ValidationUtils**: 数据验证工具，确保输入数据有效性
- **FormatUtils**: 格式化工具，处理文本和显示格式

## 配置管理

### 配置文件 (.env)
项目使用 `.env` 文件管理配置，支持自动从 `.env.config.example` 模板创建。

**关键配置项：**
- `AI_PROVIDERS`: 启用的AI供应商列表
- `GEMINI_API_KEY`: Gemini API密钥（支持多密钥）
- `OPENAI_API_KEY`: OpenAI API密钥
- `ANTHROPIC_API_KEY`: Anthropic API密钥
- `DIFY_API_KEY`: Dify API密钥
- `IFLOW_API_KEY`: iFlow API密钥
- `LOG_LEVEL`: 日志级别
- `BATCH_REQUEST_INTERVAL`: 批量请求间隔

### 配置优先级
1. 环境变量
2. .env文件
3. 内置默认值

## 开发指南

### 环境搭建
```bash
# 使用uv（推荐）
uv sync

# 或使用pip
pip install -r requirements.txt

# 配置API密钥
cp .env.config.example .env
# 编辑 .env 文件，填入API密钥
```

### 运行项目
```bash
# 交互式菜单模式
uv run python main.py

# 或模块方式
uv run python -m semantic_tester

# 命令行模式
uv run python main.py 问答测试用例.xlsx 处理后/
```

### 代码规范
- **类型注解**: 所有函数和变量必须添加类型注解
- **代码格式**: 使用black格式化代码（行宽88字符）
- **代码检查**: 使用flake8检查代码质量
- **日志规范**: 使用模块级logger，区分日志级别

### 添加新供应商
1. 在 `api/` 目录创建新的供应商类，继承 `BaseProvider`
2. 实现必要的方法：`is_configured()`, `check_semantic_similarity()`
3. 在 `ProviderManager._create_provider()` 中添加创建逻辑
4. 更新 `.env.config.example` 添加新供应商配置模板

### 测试
```bash
# 运行测试
pytest

# 代码格式检查
black --check .

# 代码质量检查
flake8
```

## 部署说明

### 生产环境准备
1. 确保Python 3.9+环境
2. 安装依赖：`pip install -r requirements.txt`
3. 配置 `.env` 文件，填入有效的API密钥
4. 准备知识库文档（Markdown格式）
5. 准备Excel测试用例文件

### Docker部署（可选）
```dockerfile
FROM python:3.9-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

CMD ["python", "main.py"]
```

### 性能优化
- **API调用**: 使用批量处理和请求间隔避免速率限制
- **Excel处理**: 增量保存，减少内存占用
- **日志**: 生产环境使用INFO级别，减少IO开销

## 与Dify Chat Tester集成

本项目完美集成 Dify Chat Tester，支持直接读取其输出文件：

1. **无缝数据流**: 无需格式转换，直接使用Dify输出文件
2. **智能格式检测**: 自动识别Dify Chat Tester输出格式
3. **动态供应商支持**: 支持所有AI供应商
4. **智能列映射**: 自动适配列映射（原始问题→问题点，{供应商名称}响应→AI客服回答）

**使用流程：**
```bash
# 1. 使用 Dify Chat Tester 生成批量测试数据
cd /path/to/dify_chat_tester
python main.py  # 选择批量模式

# 2. 使用 Semantic Tester 进行语义评估
cd /path/to/semantic_tester
uv run python main.py  # 选择Dify输出文件，自动检测格式
```

## 常见问题

### Q: 程序启动时显示"未配置供应商"？
A: 检查 `.env` 文件是否正确配置，至少需要一个有效的API密钥。

### Q: 如何处理API速率限制？
A: 程序内置自动重试机制，可通过 `BATCH_REQUEST_INTERVAL` 调整请求间隔。

### Q: Excel文件格式有什么要求？
A: 需要包含"文档名称"、"问题点"、"AI客服回答"列，列名可在运行时配置。

### Q: 知识库文档如何组织？
A: 使用Markdown格式，按主题分类，文件名与Excel中的"文档名称"列对应。

### Q: 支持哪些AI模型？
A: 取决于配置的供应商和API密钥权限，程序会自动获取可用模型列表。

## 版本历史

### v2.5+ (当前版本)
- ✅ 完成模块化重构
- ✅ 100% 类型安全 (Pylance 警告全部修复)
- ✅ 代码质量达到生产标准
- ✅ 完善的文档和测试
- 🆕 **多AI供应商支持**: Gemini、OpenAI、Anthropic、Dify、iFlow
- 🆕 **统一供应商管理**: 无缝切换，容错机制
- 🆕 **灵活配置系统**: .env文件、环境变量、交互式配置
- 🆕 **优雅降级**: 无API密钥也可启动配置

### v2.0
- ✅ 模块化架构重构
- ✅ 配置管理系统
- ✅ 多种运行模式支持
- ✅ Dify 集成功能

### v1.0
- ✅ 基础语义比对功能
- ✅ Excel 处理功能
- ✅ API 密钥管理

## 许可证

- **许可证类型**: MIT 许可证
- **中文版本**: 查看 LICENSE-CN 文件

## 联系方式

- **作者**: Mison
- **邮箱**: 1360962086@qq.com
- **GitHub**: https://github.com/MisonL

---

**最后更新**: 2025年11月20日
**项目状态**: ✅ 生产就绪 - 代码质量达到企业级标准
