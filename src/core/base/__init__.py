# 核心基础模块
# 各子模块按需导入，避免级联加载整个项目依赖树
#
# 用法:
#   from src.core.base.logger import get_logger        # 轻量，无外部依赖
#   from src.core.base.exceptions import StorageError   # 轻量，无外部依赖
#   from src.core.base.decorators import tool_handler   # 中量级
#   from src.core.base.schema import ParquetSchema      # 中量级
#   from src.core.base.result import ToolResult         # 轻量
#   from src.core.base.context import get_context       # 重型，会加载全项目依赖
#   from src.core.base.profile import ProfileEngine     # 重型
#
# 注意: 不在此处统一 re-export，因为 context.py 导入了全项目依赖
# （polars/pyarrow/sklearn/scipy/fastapi...），会导致任何
# `import src.core.base` 的进程额外占用 ~10GB 内存。
