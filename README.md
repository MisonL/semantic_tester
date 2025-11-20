<div align="center">
<h1>🚀 AI客服问答语义比对工具</h1>
</div>
<div align="center">
<img src="https://img.shields.io/badge/Python-3.9+-blue?logo=python" alt="Python版本">
<img src="https://img.shields.io/badge/License-MIT-green" alt="许可证">
<img src="https://img.shields.io/badge/Architecture-Modular-purple" alt="架构">
<img src="https://img.shields.io/badge/Type%20Safety-100%25-brightgreen" alt="类型安全">
<img src="https://img.shields.io/badge/Code%20Quality-Production%20Ready-blue" alt="代码质量">
</div>

## 📖 简介

这是一个用于评估AI客服回答与源知识库文档内容在语义上是否相符的Python工具。

**🔥 已完美集成 [Dify 聊天客户端测试工具](https://github.com/MisonL/dify_chat_tester) 项目，支持直接读取其输出文件进行语义评估！**

它通过调用Google Gemini API，对给定的问题、AI客服回答和源文档内容进行比对，判断AI客服的回答是否能够从源文档中合理推断，或是否与源文档的核心信息一致。

工具支持多密钥轮转、速率限制处理，并能从Excel文件读取数据，将比对结果实时写入Excel。

## ✨ 核心特性

### 🧠 多供应商智能语义比对
- **多AI供应商支持**: Gemini、OpenAI、Dify、iFlow
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

### 📂 知识库集成
- Markdown格式文档支持
- 按文件名自动匹配（`文档名称`列 → `处理后/文档.md`)

### 📝 完善日志
- 详细的运行日志输出到 `logs/semantic_test.log` 文件
- 控制台实时显示处理进度和关键信息

### 🏗️ 模块化架构 (v2.0+)
- **清晰的模块分离**: API、Excel、UI、配置、工具模块独立
- **易于维护和扩展**: 每个模块职责单一，便于功能扩展
- **配置管理**: 支持配置文件持久化和用户自定义设置
- **多种运行模式**: 交互式菜单模式和命令行快速处理模式

### 🔗 Dify 集成支持
- **智能格式检测**: 自动识别 Dify Chat Tester 输出格式
- **动态供应商支持**: 支持所有AI供应商（Dify、OpenAI兼容、iFlow及自定义）
- **智能列映射**: 自动适配列映射（原始问题→问题点，{供应商名称}响应→AI客服回答）
- **无缝数据流**: 无需格式转换，直接使用 Dify 输出文件

### 🛡️ 类型安全 (v2.5+)
- **100% 类型安全**: 所有 Pylance 警告已修复
- **完善的类型注解**: 使用现代 Python 类型系统
- **静态检查通过**: 符合生产环境代码质量标准

## 🔑 获取 API 密钥

### Gemini API
1. **访问 Google AI Studio**：[https://aistudio.google.com/app/apikey](https://aistudio.google.com/app/apikey) 或 Google Cloud Console
2. **创建或获取** 您的 Gemini API 密钥（支持多个密钥轮转）

### OpenAI API
1. **访问 OpenAI Platform**：[https://platform.openai.com/api-keys](https://platform.openai.com/api-keys)
2. **创建新的 API 密钥**

### Dify API
1. **访问 Dify 工作台**：登录您的 Dify 账户
2. **获取应用 API 密钥**：从应用设置中获取 API 密钥
3. **获取 API 地址**：私有化部署需要配置正确的 API 地址

### iFlow API
1. **访问 iFlow 平台**：[https://iflow.cn](https://iflow.cn)
2. **注册账户并获取 API 密钥**：从控制台获取 iFlow API 密钥
3. **支持的模型**：qwen3-max、kimi-k2-0905、glm-4.6、deepseek-v3.2 等

## ⬇️ 安装

### 使用 UV（推荐）
```bash
# 确保已安装 Python 3.9+
# 克隆仓库
# git clone https://github.com/MisonL/semantic_tester.git (假设的仓库地址)
# cd semantic_tester

# 安装依赖
uv sync
```

### 使用 pip
```bash
# 确保已安装 Python 3.9+
# 克隆仓库
# git clone https://github.com/MisonL/semantic_tester.git (假设的仓库地址)
# cd semantic_tester

# 安装依赖
pip install -r requirements.txt
```

## 🚦 使用指南

### 1. 配置 API 密钥

#### 方法一：使用 .env 文件（推荐）
1. 复制配置模板：`cp .env.config.example .env`
2. 编辑 `.env` 文件，配置您的 API 密钥：

```bash
# Gemini API（支持多密钥轮转）
GEMINI_API_KEYS=your-gemini-key1,your-gemini-key2

# OpenAI API
OPENAI_API_KEY=sk-your-openai-key

# Dify API
DIFY_API_KEY=app-your-dify-key
DIFY_BASE_URL=https://api.dify.ai/v1

# iFlow API
IFLOW_API_KEY=sk-your-iflow-key
IFLOW_MODEL=qwen3-max
IFLOW_BASE_URL=https://apis.iflow.cn/v1
```

#### 方法二：环境变量
```bash
export GEMINI_API_KEYS='API_KEY_1,API_KEY_2'
export OPENAI_API_KEY='sk-your-openai-key'
export DIFY_API_KEY='app-your-dify-key'
export IFLOW_API_KEY='sk-your-iflow-key'
```

#### 方法三：程序内交互式配置
程序运行时可通过菜单动态配置 API 密钥（临时生效）

（可选）指定 Gemini 模型版本：
```bash
export GEMINI_MODEL='models/gemini-2.5-flash'  # 默认值
```

### 2. 准备 Excel 文件
创建 Excel 文件（例如 `问答测试用例.xlsx`）需包含以下列（名称可自定义）：
- **文档名称**: 对应知识库文件名（如 `产品手册.md`）
- **问题点**: 用户提问内容
- **AI客服回答**: AI生成的回答内容

### 3. 准备知识库文档
将Markdown格式的知识库文档放置在 `处理后/` 目录（默认示例）：
```
处理后/
  产品手册.md
  常见问题.md
  使用指南.md
```

### 4. 运行程序

#### 交互式菜单模式（推荐）
```bash
# 使用 uv 运行（推荐）
uv run python main.py

# 或使用模块方式
uv run python -m semantic_tester

# 或直接运行
python main.py
```

#### 命令行模式（快速处理）
```bash
# 指定 Excel 文件和知识库目录
uv run python main.py 问答测试用例.xlsx 处理后/

# 仅指定 Excel 文件（知识库目录会交互式询问）
uv run python main.py 问答测试用例.xlsx
```

程序将通过命令行交互引导您完成 Excel 文件选择、知识库目录指定、以及各列的配置。

#### 🚀 与 Dify Chat Tester 配合使用
```bash
# 1. 使用 Dify Chat Tester 生成批量测试数据
cd /path/to/dify_chat_tester
python main.py  # 选择批量模式

# 2. 使用 Semantic Tester 进行语义评估
cd /path/to/semantic_tester
uv run python main.py  # 选择 Dify 输出文件，程序会自动检测格式
```

### 5. 查看结果
程序运行完成后，会在您指定的 Excel 文件中新增或更新 `语义是否与源文档相符` 和 `判断依据` 两列，并填充比对结果。

详细的运行日志会输出到 `logs/semantic_test.log` 文件中。

## 🏗️ 项目架构

### 模块化结构 (v2.0+)
```
semantic_tester/
├── __init__.py              # 包初始化
├── __main__.py              # 模块入口点
├── api/                     # API 接口层
│   ├── __init__.py
│   └── gemini_handler.py    # Gemini API 处理
├── config/                  # 配置管理层
│   ├── __init__.py
│   ├── environment.py       # 环境变量管理
│   └── settings.py          # 配置文件管理
├── excel/                   # Excel 处理层
│   ├── __init__.py
│   ├── processor.py         # Excel 数据处理
│   └── utils.py             # Excel 工具函数
├── ui/                      # 用户界面层
│   ├── __init__.py
│   ├── cli.py               # 命令行界面
│   └── menu.py              # 交互式菜单
└── utils/                   # 工具函数层
    ├── __init__.py
    ├── file_utils.py        # 文件操作工具
    ├── format_utils.py      # 格式化工具
    ├── logger_utils.py      # 日志工具
    └── validation_utils.py  # 验证工具
```

### 代码质量保证
- ✅ **类型安全**: 100% Pylance 警告修复
- ✅ **代码风格**: 符合 Black 标准
- ✅ **语法检查**: 所有文件通过编译检查
- ✅ **模块导入**: 完整的导入链测试
- ✅ **功能测试**: 核心组件验证通过

## ⚠️ 注意事项

1. **API Key 配置**：请确保您的 Gemini API 密钥正确且已启用 Gemini API 服务
2. **网络连接**：确保程序运行环境网络连接正常
3. **Excel 文件格式**：请确保输入的 Excel 文件格式正确，`文档名称`、`问题点` 和 `AI客服回答` 列的数据有效
4. **知识库文档**：确保 `处理后/` 目录下存在与 Excel 中 `文档名称` 对应的 Markdown 文件
5. **数据安全**：程序会实时保存 Excel 文件的处理进度，以防意外中断导致数据丢失

## 🔄 升级指南 (v2.5+)

### 从 v2.0 升级
1. **无需重新配置**: 现有的 Gemini API 配置继续有效
2. **新增供应商**: 可选择添加 OpenAI 或 Dify 供应商
3. **配置文件**: 推荐使用 `.env` 文件管理配置

### 从 v1.0 升级
1. **架构升级**: 完全重构的模块化架构
2. **配置方式**: 新增多种配置方式，推荐使用 `.env` 文件
3. **API兼容**: 保持向后兼容，现有代码无需修改

## 📈 版本历史

### v2.5+ (当前版本)
- ✅ 完成模块化重构
- ✅ 100% 类型安全 (Pylance 警告全部修复)
- ✅ 代码质量达到生产标准
- ✅ 完善的文档和测试
- 🆕 **多AI供应商支持**: Gemini、OpenAI、Dify、iFlow
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

## 📜 许可证

- **许可证类型**: [MIT 许可证](LICENSE)
- **中文版本**: [查看中文版许可证](LICENSE-CN)

## 👤 作者

- **姓名**: Mison
- **邮箱**: 1360962086@qq.com
- **GitHub**: [MisonL](https://github.com/MisonL)

---

## 🏆 项目状态

**✅ 生产就绪 - 代码质量达到企业级标准**

- 🛡️ **类型安全**: 100% 类型注解覆盖
- 🔧 **代码质量**: 通过所有静态检查
- 📊 **功能完整**: 所有核心功能正常
- 🏗️ **架构清晰**: 模块化设计，易于维护
- 📚 **文档完善**: 详细的使用和开发文档