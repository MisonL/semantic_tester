#!/bin/bash

# Semantic Tester macOS 打包脚本
# 使用方法: 在项目根目录运行 ./build/build_macos.sh

set -e  # Exit on error

# 获取脚本所在目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# 获取项目根目录（脚本所在目录的父目录）
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

# 切换到项目根目录执行所有操作
cd "$PROJECT_DIR"

echo "=========================================="
echo "Semantic Tester macOS 打包脚本"
echo "项目目录: $PROJECT_DIR"
echo "构建目录: $SCRIPT_DIR"
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
    
    # 复制必要的配置文件模板
    if [ -f "$PROJECT_DIR/.env.config.example" ]; then
        cp "$PROJECT_DIR/.env.config.example" "$PROJECT_DIR/release_macos/.env.config.example"
        # 同时提供一个可直接编辑的 .env.config，内容与模板一致
        cp "$PROJECT_DIR/.env.config.example" "$PROJECT_DIR/release_macos/.env.config"
    else
        echo "⚠️ 警告: 未找到 .env.config.example，无法拷贝配置文件模板"
    fi

    # 创建空的知识库目录
    mkdir -p "$PROJECT_DIR/release_macos/kb-docs"
    
    # 复制文档文件（如果存在）
    [ -f "$PROJECT_DIR/README.md" ] && cp "$PROJECT_DIR/README.md" "$PROJECT_DIR/release_macos/"
    # [ -d "$PROJECT_DIR/docs" ] && cp -r "$PROJECT_DIR/docs" "$PROJECT_DIR/release_macos/"
    
    # 拷贝统一的用户使用指南（保持原始文件名）
    if [ -f "$PROJECT_DIR/docs/用户使用指南.md" ]; then
        cp "$PROJECT_DIR/docs/用户使用指南.md" "$PROJECT_DIR/release_macos/用户使用指南.md"
    else
        echo "⚠️ 警告: 未找到 docs/用户使用指南.md，无法生成使用说明文档"
    fi
    
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
    echo "2. 阅读 '用户使用指南.md'"
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
