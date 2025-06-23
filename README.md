<div align="center">
<h1>🚀 AI客服问答语义比对工具</h1>
</div>
<div align="center">
![Python版本](https://img.shields.io/badge/Python-3.8+-blue?logo=python) ![许可证](https://img.shields.io/badge/License-MIT-green)
</div>

## 📖 简介
这是一个用于评估AI客服回答与源知识库文档内容在语义上是否相符的Python工具。
**建议与 [Dify 聊天客户端测试工具](https://github.com/MisonL/dify_chat_tester) 项目搭配使用，以实现Dify应用问答效果的自动化评估。**
它通过调用Google Gemini API，对给定的问题、AI客服回答和源文档内容进行比对，
判断AI客服的回答是否能够从源文档中合理推断，或是否与源文档的核心信息一致。
工具支持多密钥轮转、速率限制处理，并能从Excel文件读取数据，将比对结果实时写入Excel。

## ✨ 核心特性
### 🧠 智能语义比对
- 基于Google Gemini API的高级语义分析
- 判断AI回答与知识库文档的语义一致性
- 输出JSON格式的比对结果和判断依据

### ⚙️ 强大的API管理
- 多密钥自动轮转和冷却处理
- 速率限制(429)自动重试机制
- 首次调用前密钥有效性验证

### 📊 实时Excel处理
- **增量保存**: 每条记录处理后立即保存结果
- 灵活列名配置，支持自定义列
- 自动创建结果列（语义是否相符/判断依据）
- 合并单元格安全写入

### 📂 知识库集成
- Markdown格式文档支持
- 按文件名自动匹配（`文档名称`列 → `处理后/文档.md`)

### 📝 完善日志
-   详细的运行日志输出到 `logs/semantic_test.log` 文件。
-   控制台实时显示处理进度和关键信息。

## 🔑 获取 Gemini API 密钥
1.  **访问 Google AI Studio**：[https://aistudio.google.com/app/apikey](https://aistudio.google.com/app/apikey) 或 Google Cloud Console。
2.  **创建或获取** 您的 Gemini API 密钥。

## ⬇️ 安装
```bash
# 确保已安装 Python 3.8+
# 克隆仓库
# git clone https://github.com/MisonL/semantic_tester.git (假设的仓库地址)
# cd semantic_tester

# 安装依赖
pip install -r requirements.txt
```

## 🚦 使用指南
### 1. 设置环境变量
将您的 Gemini API 密钥配置到环境变量 `GEMINI_API_KEYS` 或 `GOOGLE_API_KEY` 中。支持多密钥自动轮转和冷却处理：
```bash
export GEMINI_API_KEYS='API_KEY_1,API_KEY_2,API_KEY_3'
```
（可选）指定 Gemini 模型版本：
```bash
export GEMINI_MODEL='models/gemini-2.5-flash'  # 默认值
```

### 2. 准备 Excel 文件
创建 Excel 文件（例如 `问答测试用例.xlsx`）需包含以下列（名称可自定义）：
- **文档名称**: 对应知识库文件名（如 `产品手册.md`)
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
```bash
python semantic_tester.py
```
程序将通过命令行交互引导您完成 Excel 文件选择、知识库目录指定、以及各列的配置。

### 5. 查看结果
程序运行完成后，会在您指定的 Excel 文件中新增或更新 `语义是否与源文档相符` 和 `判断依据` 两列，并填充比对结果。
详细的运行日志会输出到 `logs/semantic_test.log` 文件中。

## ⚠️ 注意事项
1.  **API Key 配置**：请确保您的 Gemini API 密钥正确且已启用 Gemini API 服务。
2.  **网络连接**：确保程序运行环境网络连接正常。
3.  **Excel 文件格式**：请确保输入的 Excel 文件格式正确，`文档名称`、`问题点` 和 `AI客服回答` 列的数据有效。
4.  **知识库文档**：确保 `处理后/` 目录下存在与 Excel 中 `文档名称` 对应的 Markdown 文件。
5.  **数据安全**：程序会实时保存 Excel 文件的处理进度，以防意外中断导致数据丢失。

## 📜 许可证
-   **许可证类型**: [MIT 许可证](LICENSE)
-   **中文版本**: [查看中文版许可证](LICENSE-CN)

## 👤 作者
-   **姓名**: Mison
-   **邮箱**: 1360962086@qq.com
-   **GitHub**: [MisonL](https://github.com/MisonL)
