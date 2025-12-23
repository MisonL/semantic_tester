# 📚 开发者指南 (v4.0.0)

## 概述

本文档为开发者提供详细的技术指南，包括项目架构、开发流程、代码规范和最佳实践。

## 🏗️ 项目架构详解

### 分层架构设计 (v4.0.0 多渠道并发架构)

```
┌─────────────────────────────────────────────────────────────┐
│                    用户界面层 (UI)                           │
│  ┌─────────────────┐  ┌─────────────────┐  ┌──────────────┐ │
│  │   CLI 终端界面    │  │   WorkerTable   │  │  进度面板     │ │
│  │   (cli.py)       │  │   (worker_ui)   │  │  (rich.Live) │ │
│  └─────────────────┘  └─────────────────┘  └──────────────┘ │
└─────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────┐
│                   业务逻辑层 (v4.0.0 新增)                    │
│  ┌─────────────────┐  ┌─────────────────┐  ┌──────────────┐ │
│  │   多渠道管理      │  │   并发任务队列    │  │  结果聚合     │ │
│  │(ProviderManager) │  │ (ThreadPool)    │  │  (callback)  │ │
│  └─────────────────┘  └─────────────────┘  └──────────────┘ │
└─────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────┐
│                   API 供应商层                               │
│  ┌──────┐  ┌──────┐  ┌──────┐  ┌──────┐  ┌──────┐          │
│  │Gemini│  │OpenAI│  │Claude│  │ Dify │  │iFlow │          │
│  └──────┘  └──────┘  └──────┘  └──────┘  └──────┘          │
│           全部支持流式输出和思维链展示 ✅                      │
└─────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────┐
│                    基础设施层                               │
│  ┌─────────────────┐  ┌─────────────────┐  ┌──────────────┐ │
│  │   文件操作       │  │   日志管理       │  │  配置加载     │ │
│  │ (file_utils.py)  │  │(logger_utils.py)│  │(env_loader)  │ │
│  └─────────────────┘  └─────────────────┘  └──────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

### 数据流图 (v4.0.0)

```
Excel文件 → 任务队列 ─┬→ Channel 1 (Worker 1-N) ─┬→ 结果聚合 → Excel保存
                     ├→ Channel 2 (Worker 1-N) ─┤
                     └→ Channel N (Worker 1-N) ─┘
                           ↓
                    实时 UI 更新 (WorkerTableUI)
```

## 🔧 开发环境设置

### 环境要求

- Python 3.10+
- UV (推荐) 或 pip
- Git

### 开发环境搭建

```bash
# 1. 克隆项目
git clone <repository-url>
cd semantic_tester

# 2. 创建虚拟环境
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# 或 .venv\Scripts\activate  # Windows

# 3. 安装依赖
uv sync  # 推荐
# 或 pip install -r requirements.txt

# 4. 安装开发工具
pip install black flake8 pytest mypy

# 5. 设置 pre-commit hooks (可选)
pre-commit install
```

## 📝 代码规范

### 类型注解规范

```python
# ✅ 正确的类型注解
def process_data(
    input_file: str,
    output_dir: Optional[str] = None
) -> Dict[str, Any]:
    """处理数据文件"""
    pass

# ✅ 使用类型别名
from typing import Dict, List, Optional, Any
FilePath = str
ConfigDict = Dict[str, Any]
```

### 错误处理规范

```python
# ✅ 完善的错误处理
try:
    result = api_call()
except APIError as e:
    logger.error(f"API调用失败: {e}")
    raise
except Exception as e:
    logger.error(f"未知错误: {e}")
    raise
```

### 日志记录规范

```python
# ✅ 结构化日志记录
logger.info("开始处理文件", extra={"file": file_path})
logger.warning("API调用接近限制", extra={"retry_count": retry_count})
logger.error("处理失败", exc_info=True)
```

## 🧪 测试指南

### 测试结构

```
tests/
├── unit/                   # 单元测试
│   ├── test_api/
│   ├── test_excel/
│   └── test_utils/
├── integration/            # 集成测试
│   ├── test_end_to_end.py
│   └── test_api_integration.py
└── fixtures/              # 测试数据
    ├── sample_excel.xlsx
    └── test_documents/
```

### 运行测试

```bash
# 运行所有测试
pytest

# 运行特定测试
pytest tests/unit/test_api/

# 生成覆盖率报告
pytest --cov=semantic_tester --cov-report=html
```

### 测试示例

```python
import pytest
from semantic_tester.api import GeminiAPIHandler

class TestGeminiAPIHandler:
    def test_init_with_keys(self):
        """测试使用API密钥初始化"""
        handler = GeminiAPIHandler(["test_key"])
        assert handler.api_keys == ["test_key"]

    def test_validate_key_success(self, mock_api):
        """测试密钥验证成功"""
        handler = GeminiAPIHandler(["valid_key"])
        assert handler.validate_api_key("valid_key") == True
```

## 🔄 开发流程

### 1. 功能开发流程

```bash
# 1. 创建功能分支
git checkout -b feature/new-feature

# 2. 开发功能
# 编写代码...

# 3. 运行测试和检查
pytest
black semantic_tester/
flake8 semantic_tester/
mypy semantic_tester/

# 4. 提交代码
git add .
git commit -m "feat: 添加新功能"

# 5. 推送和创建PR
git push origin feature/new-feature
```

### 2. Bug 修复流程

```bash
# 1. 创建bug修复分支
git checkout -b fix/bug-description

# 2. 定位和修复
# 调试和修复...

# 3. 添加回归测试
# 编写测试用例...

# 4. 验证修复
pytest tests/regression/

# 5. 提交修复
git commit -m "fix: 修复具体问题描述"
```

## 📊 性能优化指南

### API 调用优化

```python
# ✅ 批量处理和缓存
class GeminiAPIHandler:
    def __init__(self):
        self._response_cache = {}

    def check_semantic_similarity(self, question: str, answer: str, doc: str):
        cache_key = hash((question, answer, doc))
        if cache_key in self._response_cache:
            return self._response_cache[cache_key]

        result = self._api_call(question, answer, doc)
        self._response_cache[cache_key] = result
        return result
```

### 内存管理优化

```python
# ✅ 使用生成器处理大文件
def process_large_excel(file_path: str):
    workbook = load_workbook(file_path, read_only=True)
    for row in workbook.active.iter_rows(values_only=True):
        yield process_row(row)
    workbook.close()
```

## 🔍 调试指南

### 日志调试

```python
import logging

# 启用详细日志
logging.basicConfig(level=logging.DEBUG)

# 在关键位置添加调试日志
logger.debug("进入函数", extra={"function": "process_data"})
logger.debug("变量状态", extra={"variable": value})
```

### 性能分析

```python
import cProfile
import pstats

# 性能分析
profiler = cProfile.Profile()
profiler.enable()

# 执行代码
result = your_function()

profiler.disable()
stats = pstats.Stats(profiler)
stats.sort_stats('cumulative')
stats.print_stats(10)  # 显示前10个最耗时的函数
```

## 📈 监控和维护

### 关键指标监控

- API 调用成功率
- 平均响应时间
- 错误率统计
- 内存使用情况

### 日志监控

```python
# 结构化日志便于监控
logger.info("API调用统计", extra={
    "total_calls": total_calls,
    "success_rate": success_rate,
    "avg_response_time": avg_time
})
```

## 🚀 部署指南

### Docker 部署

```dockerfile
FROM python:3.9-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
CMD ["python", "main.py"]
```

### 生产环境配置

```python
# 生产环境配置
import os
from semantic_tester.config import Config

PRODUCTION_CONFIG = {
    "log_level": "INFO",
    "max_retries": 3,
    "timeout": 30,
    "cache_enabled": True
}
```

## 📚 API 参考

### 核心类和方法

```python
class GeminiAPIHandler:
    def __init__(self, api_keys: List[str])
    def validate_api_key(self, api_key: str) -> bool
    def rotate_key(self) -> str
    def check_semantic_similarity(self, question: str, answer: str, doc: str) -> Dict

class ExcelProcessor:
    def __init__(self, file_path: str)
    def load_data(self) -> pd.DataFrame
    def save_result(self, row_index: int, result: str, reason: str)
    def get_row_data(self, row_index: int) -> Dict[str, str]
```

## 🔧 故障排除

### 常见问题及解决方案

#### 1. API 密钥问题

```python
# 问题：API密钥无效
# 解决：检查密钥格式和网络连接
def test_api_connection():
    try:
        client = genai.Client(api_key=test_key)
        response = client.models.get(model="models/gemini-2.5-flash")
        return response is not None
    except Exception as e:
        logger.error(f"API连接测试失败: {e}")
        return False
```

#### 2. Excel 文件读取问题

```python
# 问题：文件格式不支持
# 解决：检查文件扩展名和格式
def validate_excel_file(file_path: str) -> bool:
    if not file_path.endswith(('.xlsx', '.xls')):
        return False
    try:
        pd.read_excel(file_path, nrows=1)
        return True
    except Exception:
        return False
```

## 📋 最佳实践清单

### 代码质量

- [ ] 所有函数都有类型注解
- [ ] 错误处理完善
- [ ] 日志记录适当
- [ ] 代码风格一致
- [ ] 单元测试覆盖

### 性能优化

- [ ] 避免重复 API 调用
- [ ] 使用缓存机制
- [ ] 及时释放资源
- [ ] 批量处理数据

### 安全考虑

- [ ] API 密钥安全存储
- [ ] 输入数据验证
- [ ] 错误信息脱敏
- [ ] 权限控制适当

---

## 🤝 贡献指南

欢迎贡献代码！请遵循以下步骤：

1. Fork 项目
2. 创建功能分支
3. 编写代码和测试
4. 确保所有检查通过
5. 提交 Pull Request

感谢您的贡献！🎉
