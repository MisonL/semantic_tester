#!/bin/bash

# macOS Build Script for Semantic Tester
# Usage: Run ./build/build_macos.sh from project root

set -e  # Exit on error

# 获取脚本所在目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# 获取项目根目录（脚本所在目录的父目录）
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

# 切换到项目根目录执行所有操作
cd "$PROJECT_DIR"

echo "=========================================="
echo "Semantic Tester macOS Build Script"
echo "Project directory: $PROJECT_DIR"
echo "Build directory: $SCRIPT_DIR"
echo "=========================================="

# 检查 uv 是否安装
if ! command -v uv &> /dev/null; then
    echo "❌ 错误: uv 未安装"
    echo "请先安装 uv: curl -LsSf https://astral.sh/uv/install.sh | sh"
    exit 1
fi

# 检查 Python 版本
echo "🐍 检查 Python 版本..."
uv run python --version

# 安装/更新依赖
echo "📦 安装/更新依赖..."
uv sync

# 安装 PyInstaller
echo "🔧 安装 PyInstaller..."
uv add --dev pyinstaller

# 清理之前的构建（只清理build目录下的临时文件，保留spec文件）
echo "🧹 清理之前的构建..."
rm -rf "$PROJECT_DIR/build/semantic_tester" 2>/dev/null || true
rm -rf "$PROJECT_DIR/build/semantic_tester.dist" 2>/dev/null || true
rm -rf "$PROJECT_DIR/build/semantic_tester.build" 2>/dev/null || true
rm -rf "$PROJECT_DIR/dist" 2>/dev/null || true

# 优先使用build目录的spec文件
SPEC_FILE="$SCRIPT_DIR/semantic_tester.spec"
if [ ! -f "$SPEC_FILE" ]; then
    echo "❌ 错误: 找不到 spec 文件: $SPEC_FILE"
    exit 1
fi

echo "📄 使用 spec 文件: $SPEC_FILE"

# 运行 PyInstaller
echo "🚀 开始打包..."
uv run pyinstaller "$SPEC_FILE"

# 检查打包结果
if [ -f "$PROJECT_DIR/dist/semantic_tester" ]; then
    echo "✅ 打包成功！"
    echo "📁 可执行文件位置: $PROJECT_DIR/dist/semantic_tester"
    
    # 创建发布目录
    mkdir -p "$PROJECT_DIR/release_macos"
    
    # 复制文件到发布目录
    cp "$PROJECT_DIR/dist/semantic_tester" "$PROJECT_DIR/release_macos/"
    
    # 复制必要的配置文件
    cp "$PROJECT_DIR/.env.config.example" "$PROJECT_DIR/release_macos/"
    
    # 复制文档文件（如果存在）
    [ -f "$PROJECT_DIR/README.md" ] && cp "$PROJECT_DIR/README.md" "$PROJECT_DIR/release_macos/"
    # [ -d "$PROJECT_DIR/docs" ] && cp -r "$PROJECT_DIR/docs" "$PROJECT_DIR/release_macos/"
    
    # 创建使用说明文档
    cat > "$PROJECT_DIR/release_macos/使用说明.md" << 'EOF'
# 🤖 Semantic Tester 使用说明书

<div align="center">

## 📚 普通用户使用指南

### 🌟 从零开始，轻松上手

#### 本指南将带您完成从环境准备到程序使用的全过程

</div>

---

## 📑 目录

| 序号 | 内容                                            |
| ---- | ----------------------------------------------- |
| 1️⃣   | [准备工作](#1-准备工作)                         |
| 2️⃣   | [启动软件](#2-启动软件)                         |
| 3️⃣   | [使用软件](#3-使用软件)                         |
| 4️⃣   | [常见问题](#4-常见问题)                         |

---

## 1. ✅ 准备工作

在开始使用之前，请确保您已经完成了以下准备工作：

### 1.1 解压文件
- 请确保您已经解压了本软件压缩包。
- 建议解压到一个路径不包含中文的文件夹中（例如 `D:\Tools\SemanticTester`）。

### 1.2 配置文件
1. 在本文件夹中，找到名为 `.env.config.example` 的文件。
2. 将其复制一份并重命名为 `.env.config`（注意前面的点）。
3. 使用文本编辑器（如记事本）打开 `.env.config` 文件。
4. 填入您的 API Key 和其他配置信息。

### 1.3 准备知识库
1. 在本文件夹中创建一个名为 `kb-docs` 的文件夹（如果不存在）。
2. 将您的知识库文档（支持 .txt, .md, .pdf 等格式）放入其中。
3. 软件会自动读取该文件夹下的所有文档作为知识库。

---

## 2. 🚀 启动软件

### macOS 用户

1. **双击运行**
   - 双击运行 `semantic_tester` 程序。

2. **处理安全警告（首次运行）**
   - 如果系统提示"无法打开，因为无法验证开发者"：
     1. 点击"取消"。
     2. 按住键盘上的 **Control** 键。
     3. 鼠标右键点击（或双指点击）`semantic_tester` 图标。
     4. 在弹出的菜单中选择"打开"。
     5. 在弹出的对话框中再次点击"打开"。

### Windows 用户

1. **双击运行**
   - 双击运行 `semantic_tester.exe` 程序。

2. **处理安全警告（如果出现）**
   - 如果 Windows Defender 提示风险：
     1. 点击"更多信息"。
     2. 点击"仍要运行"。

---

## 3. 🎮 使用软件

软件启动后，您将看到交互式菜单，请按照屏幕上的提示进行操作。

### 3.1 功能选择
- **批量测试**：选择 Excel 文件进行批量测试。
- **单次测试**：直接输入问题进行测试。

### 3.2 匹配模式
- **全量文档匹配**：将问题与知识库中的所有文档进行比对。
- **指定文档匹配**：仅与 Excel 中指定的文档进行比对（默认模式）。

### 3.3 查看结果
- 测试结果将保存在本文件夹中，文件名通常包含时间戳。
- 您可以直接打开生成的 Excel 文件查看详细的比对结果。

---

## 4. ❓ 常见问题

### Q1: 软件闪退怎么办？
- **检查配置**：请检查 `.env.config` 文件中的配置是否正确，特别是 API Key。
- **检查网络**：确保您的网络连接正常，能够访问相应的 AI 服务（如 OpenAI, Google Gemini 等）。

### Q2: 无法读取文档？
- **检查路径**：确保 `kb-docs` 文件夹存在且路径正确。
- **检查格式**：确保文档格式是支持的（.txt, .md, .pdf）。

### Q3: 结果不准确？
- **检查模型**：尝试更换更强大的 AI 模型（如 GPT-4, Claude 3.5 Sonnet）。
- **优化文档**：检查知识库文档的内容是否清晰、准确。

---

<div align="center">
  <p>如有更多问题，请联系技术支持。</p>
</div>
EOF
    
    # 获取版本号
    VERSION=$(grep -m 1 'version = ' "$PROJECT_DIR/pyproject.toml" | sed 's/version = "//;s/"//')
    if [ -z "$VERSION" ]; then
        VERSION="unknown"
    fi
    
    # 压缩发布包
    cd "$PROJECT_DIR"
    RELEASE_NAME="semantic_tester_macos_v${VERSION}_$(date +%Y%m%d_%H%M%S).tar.gz"
    tar -czf "$RELEASE_NAME" -C release_macos .
    
    echo "📦 发布包已创建: $PROJECT_DIR/$RELEASE_NAME"
    echo ""
    echo "📋 使用说明:"
    echo "1. 解压 $RELEASE_NAME"
    echo "2. 阅读 '使用说明.md'"
    echo "3. 按说明配置并运行程序"
    echo ""
    echo "🎉 打包完成！"
    
    # 清理临时文件
    echo "🧹 清理临时文件..."
    rm -rf "$PROJECT_DIR/build/semantic_tester" 2>/dev/null || true
    rm -rf "$PROJECT_DIR/build/semantic_tester.dist" 2>/dev/null || true
    rm -rf "$PROJECT_DIR/build/semantic_tester.build" 2>/dev/null || true
    echo "✅ 清理完成"
else
    echo "❌ 打包失败！"
    echo "请检查错误信息并重试"
    exit 1
fi
