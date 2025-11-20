# Dify Chat Tester 与 Semantic Tester 集成使用指南

## 🎯 概述

本指南详细说明如何将 **Dify Chat Tester** 的输出直接用于 **Semantic Tester** 进行语义质量评估，实现完整的AI客服测试→评估流程。

## 🔄 工作流程

```
Dify Chat Tester (批量AI询问) → Excel输出 → Semantic Tester (语义评估) → 综合质量报告
```

## 📋 前置条件

### 1. 环境准备
```bash
# 安装 uv (如果尚未安装)
curl -LsSf https://astral.sh/uv/install.sh | sh

# 克隆或下载 semantic_tester 项目
cd semantic_tester

# 安装依赖
uv sync
```

### 2. 环境变量配置
```bash
# 设置 Gemini API 密钥
export GEMINI_API_KEYS='your_gemini_key_1,your_gemini_key_2'

# 可选：指定模型版本
export GEMINI_MODEL='models/gemini-2.5-flash'
```

### 3. 知识库文档准备
在 `semantic_tester/处理后/` 目录下放置对应的 Markdown 知识库文档：

```
处理后/
├── AI知识库.md
├── 产品手册.md
├── 使用指南.md
└── 常见问题.md
```

## 🚀 快速开始

### 步骤 1: 使用 Dify Chat Tester 生成测试数据

1. **运行 Dify Chat Tester**
   ```bash
   cd /path/to/dify_chat_tester
   python main.py
   ```

2. **选择批量模式**
   - 选择选项 `2` (批量查询模式)
   - 选择包含问题的 Excel 文件
   - 配置 AI 供应商和参数

3. **获取输出文件**
   - 输出文件格式：`batch_query_log_YYYYMMDD_HHMMSS.xlsx`
   - 包含字段：时间戳、角色、原始问题、Dify响应、是否成功等

### 步骤 2: 使用 Semantic Tester 进行语义评估

1. **启动 Semantic Tester**
   ```bash
   cd semantic_tester
   uv run python semantic_tester.py
   ```

2. **智能格式检测**
   - 选择 Dify Chat Tester 生成的 Excel 文件
   - 程序会自动检测格式并显示：
   ```
   ✅ 检测到 Dify Chat Tester 输出格式！
   将自动适配列映射关系：
     • 原始问题 → 问题点
     • OpenAI 兼容接口响应 → AI客服回答
     • 文档名称 → 需要手动指定
   ```

   **多响应列处理：**
   如果文件包含多个供应商的响应列，程序会提示选择：
   ```
   发现多个响应列，请选择要使用的一个：
     1. Dify响应
     2. OpenAI 兼容接口响应
     3. iFlow响应

   请输入选择 (1-3, 默认: 1):
   ```

   - 支持所有供应商的响应列名（Dify响应、iFlow响应、自定义AI响应等）
   - 智能选择：针对混合数据文件，可选择特定供应商进行评估

3. **自动配置**
   - 程序自动添加"文档名称"列
   - 自动配置列映射关系
   - 选择 `Y` 使用自动配置

4. **配置知识库目录**
   ```
   请输入知识库文档目录路径: 处理后/
   ```

5. **完成配置**
   - 配置结果保存列
   - 设置输出文件路径
   - 开始语义分析

### 步骤 3: 查看评估结果

1. **控制台输出**
   ```
   正在处理第 1/3 条记录...
   语义比对结果：是 (问题: '什么是人工智能？...')
   已保存结果到 output.xlsx (已处理 1 条记录)
   ```

2. **Excel 结果文件**
   - 原始数据 + 语义评估结果
   - 新增列：
     - `语义是否与源文档相符`: "是" / "否"
     - `判断依据`: 详细的判断理由

3. **详细日志**
   ```bash
   tail -f logs/semantic_test.log
   ```

## 📊 数据格式说明

### Dify Chat Tester 输出格式

| 列名 | 数据类型 | 说明 | 示例 |
|------|----------|------|------|
| 时间戳 | DateTime | 记录处理时间 | 2025-11-18 16:24:25 |
| 角色 | String | 对话发起角色 | 员工 |
| **原始问题** | Text | 用户提问内容 | 什么是人工智能？ |
| **{供应商名称}响应** | LongText | AI的回答内容 | 您好！人工智能是... |
| 是否成功 | Boolean | 请求状态标识 | True |
| 错误信息 | Text | 失败错误描述 | (空) |
| 对话ID | String | 唯一标识符 | conv-001 |

#### 支持的响应列名格式

根据配置的AI供应商，响应列名会动态生成：

| 供应商 | 响应列名格式 | 实际列名示例 |
|--------|-------------|-------------|
| Dify | `Dify响应` | Dify响应 |
| OpenAI 兼容 | `OpenAI 兼容接口响应` | OpenAI 兼容接口响应 |
| iFlow | `iFlow响应` | iFlow响应 |
| 自定义供应商 | `{自定义名称}响应` | 智谱AI响应、百度AI响应等 |

**检测规则：**
- 自动识别以"响应"结尾的列作为AI回答列
- 支持"原始问题"、"用户输入"、"问题"作为问题列
- 兼容各种自定义供应商名称

### Semantic Tester 期望格式

| 列名 | 数据类型 | 说明 | 来源于 |
|------|----------|------|--------|
| **文档名称** | String | 知识库文件名 | 自动添加，需手动填写 |
| **问题点** | Text | 用户提问内容 | Dify的"原始问题" |
| **AI客服回答** | Text | AI的回答内容 | Dify的"Dify响应" |

## 🔧 高级配置

### 1. 自定义文档名称策略

#### 统一文档名
所有问题使用同一个知识库文档：
```python
# 在自动添加的"文档名称"列中填写
AI知识库.md
```

#### 分类文档名
根据问题内容分配不同文档：
```python
# 问题1: "什么是人工智能？" → AI基础知识.md
# 问题2: "Python特点？" → 编程语言.md
# 问题3: "Dify功能？" → 产品文档.md
```

### 2. 批量处理多个文件

创建批量处理脚本：
```bash
#!/bin/bash
# process_multiple.sh

for file in batch_query_log_*.xlsx; do
    echo "处理文件: $file"
    uv run python semantic_tester.py << EOF
$file
处理后/
Y
语义是否与源文档相符
判断依据
N
${file%.xlsx}_评估结果.xlsx
EOF
done
```

### 3. 结果分析

#### 成功率统计
```python
import pandas as pd

df = pd.read_excel('评估结果.xlsx')
success_rate = (df['语义是否与源文档相符'] == '是').mean() * 100
print(f"语义相符率: {success_rate:.1f}%")
```

#### 问题分类分析
```python
# 按文档名称分析
doc_stats = df.groupby('文档名称')['语义是否与源文档相符'].value_counts(normalize=True)
print(doc_stats)
```

## ⚠️ 常见问题

### Q1: 程序无法识别 Dify 格式？
**A:** 确保输出文件包含 `原始问题` 和 `Dify响应` 两列。

### Q2: "文档名称"列如何填写？
**A:**
- 单一知识库：填写统一的文档名（如 `AI知识库.md`）
- 多知识库：根据问题内容填写对应的文档名
- 确保文档存在于 `处理后/` 目录

### Q3: Gemini API 调用失败？
**A:**
- 检查环境变量 `GEMINI_API_KEYS` 是否正确设置
- 确认网络连接正常
- 检查 API 密钥是否有效且有配额

### Q4: 处理大量数据时速度慢？
**A:**
- 使用多个 API 密钥轮转
- 调整请求间隔时间
- 考虑分批处理

### Q5: Excel 文件读取错误？
**A:**
- 确保文件未被其他程序占用
- 检查文件格式是否正确
- 尝试重新导出或转换文件格式

### Q6: 文件中有多个响应列，如何选择？
**A:**
- 程序会自动检测所有以"响应"结尾的列
- 根据提示数字选择要评估的供应商响应
- 可以分别对不同供应商进行多次评估
- 例如：先选择"Dify响应"评估，再选择"OpenAI响应"评估

## 🎉 最佳实践

### 1. 数据质量优化
- 确保问题表述清晰明确
- AI 回答内容完整且相关
- 知识库文档内容准确

### 2. 工作流程优化
- 先小批量测试，确认配置正确
- 定期备份原始数据和结果
- 建立标准化的文档命名规范

### 3. 结果应用
- 根据评估结果优化 AI 模型配置
- 更新和完善知识库内容
- 建立质量监控和反馈机制

## 📚 扩展阅读

- [Semantic Tester README.md](README.md)
- [Dify Chat Tester 项目文档](https://github.com/MisonL/dify_chat_tester)
- [Google Gemini API 文档](https://ai.google.dev/docs)

---

**作者**: Mison
**邮箱**: 1360962086@qq.com
**更新时间**: 2025-11-18