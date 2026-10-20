"""
LLM Wiki 测试会话配置
确保项目根目录在 sys.path 中，使 `import knowledge_engine` 可用。
"""
import os
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)
