import sys
from pathlib import Path

# 将 src 添加到搜索路径，确保直接运行 python main.py 即可执行
src_path = Path(__file__).resolve().parent / "src"
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

from starrail_tools.main import main

if __name__ == "__main__":
    main()
