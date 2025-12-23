# 更新日志 (Changelog)

本项目的所有重要更改都将记录在此文件中。

格式基于 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.0.0/)，
并且本项目遵循 [语义化版本控制 (Semantic Versioning)](https://semver.org/lang/zh-CN/spec/v2.0.0.html)。

## [v4.0.0] - 2025-12-23

### 新增 (Added)

- **多渠道架构**: 全面切换到支持多 AI 渠道的并发模型。
- **环境配置**: 新增 `AI_CHANNEL_*` 环境变量，支持灵活配置。
- **API 密钥预校验**: 在任务执行前自动验证并过滤无效的 API 密钥。
- **WorkerTableUI 升级**:
  - 全屏渲染模式，消除终端显示残留。
  - 实时显示当前处理的问题和流式回答预览。
  - 智能 JSON 解析，以格式化的 "是/否/不确定 | 理由" 下展示。
- **Windows 支持**: 增强打包配置，通过 `pyi_rth_ssl_fix.py` 解决 SSL DLL 加载问题。

### 变更 (Changed)

- **供应商管理 (ProviderManager)**: 统一管理所有供应商的生命周期，移除了旧的单供应商逻辑。
- **项目结构**: 清理了代码库，移除了未使用的 Hooks 和临时文件。
- **UI 体验**: 改进了状态图标 (🔍 分析中 / 💭 思考中 / ✅ 完成)，并防止列文本换行。

### 修复 (Fixed)

- **Windows 兼容性**: 解决了 PyInstaller 打包时出现的 `ImportError: DLL load failed while importing _ssl` 错误。
- **启动警告**: 屏蔽了来自 `google.api_core` 的 `FutureWarning`，使启动日志更清爽。
- **测试**: 修复了 11 个过时的测试；删除了针对已弃用方法的测试。
- **代码质量**: 解决了所有 Pylance/flake8 代码检查错误 (F401, F811, F821, F841, E722)。

## [v3.0.1] - 2025-12-05

### 变更 (Changed)

- **架构**: 重构 `SemanticTestApp` 以支持 `EnvManager` 和 `Config` 的依赖注入。
- **错误处理**: 引入 `exceptions.py` 以建立统一的异常处理机制。

### 新增 (Added)

- **优雅退出**: 添加了 `Ctrl+C` 中断处理及数据保存保护。
- **自动保存**: 实现了处理过程中的定期数据保存（每 10 条记录）。
- **测试**: 为异常处理模块添加了单元测试。

## [v3.0.0] - 2025-12-03

### 新增 (Added)

- **自定义提示词**: 支持 `SEMANTIC_CHECK_PROMPT` 配置，支持占位符 (`{question}`, `{ai_answer}` 等)。
- **UI 增强**: 集成 `rich` 库以获得更好的终端视觉效果和启动加载动画。
- **性能**: 实现了模块懒加载以提高启动速度。

### 变更 (Changed)

- **流式显示**: 优化显示逻辑，优先展示问题/回答，然后再展示思考过程。
- **配置**: 改进了 `.gitignore` 并添加了默认的 `coverage` 配置。

### 修复 (Fixed)

- **代码语法**: 验证并修复了 `main.py` 中的语法问题。
- **字符串格式化**: 使用基于回调的替换增强了 `format_utils` 对关键字冲突的健壮性。

## [v2.5.0] - 2025-11-22

### 新增 (Added)

- **多供应商支持**: 集成了 Gemini, OpenAI, Dify 和 iFlow 供应商。
- **类型安全**: 实现了 100% 的类型提示覆盖率。

## [v2.0.0] - 2025-11-20

### 新增 (Added)

- 模块化架构重构。
- 配置管理系统。
- 多运行模式支持。
- Dify 集成。

## [v1.0.0] - 2025-06-23

### 新增 (Added)

- 基础语义比对功能。
- Excel 文件处理。
- API 密钥管理。
