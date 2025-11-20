"""
Semantic Tester 包主入口点

支持 python -m semantic_tester 命令
"""

import sys
from pathlib import Path

# 添加项目根目录到 sys.path，以便导入 main.py
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from main import main  # type: ignore

if __name__ == "__main__":
    main()
