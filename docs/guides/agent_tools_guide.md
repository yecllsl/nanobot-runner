# Agent 工具扩展指南

本文档描述如何为 Nanobot Runner 新增 Agent 工具。

---

## 1. 工具架构

```mermaid
graph LR
    A[LLM 决策] --> B[选择工具]
    B --> C[BaseTool.execute]
    C --> D[RunnerTools 调用]
    D --> E[StorageManager/AnalyticsEngine]
    E --> F[返回结果]
```

---

## 2. 新增工具步骤

### 步骤 1：创建工具类

继承 `BaseTool` 并实现必要属性和方法：

```python
# src/agents/tools.py
from src.agents.base import BaseTool

class MyNewTool(BaseTool):
    name: str = "my_new_tool"
    description: str = "工具描述，LLM会看到这段文字"
    parameters: dict = {
        "type": "object",
        "properties": {
            "param1": {"type": "string", "description": "参数说明"},
            "param2": {"type": "number", "description": "可选参数"}
        },
        "required": ["param1"]
    }
    
    async def execute(self, **kwargs) -> dict:
        """执行工具逻辑"""
        param1 = kwargs.get("param1")
        
        # 业务逻辑
        result = self._process(param1)
        
        return {
            "success": True,
            "data": result
        }
    
    def _process(self, param: str) -> dict:
        """内部处理逻辑"""
        return {"result": param}
```

### 步骤 2：在 RunnerTools 中注册

```python
# src/agents/tools.py
class RunnerTools:
    def __init__(self):
        self.tools = {
            "get_running_stats": GetRunningStatsTool(),
            "get_recent_runs": GetRecentRunsTool(),
            "my_new_tool": MyNewTool(),  # 添加新工具
            ...
        }
```

### 步骤 3：更新 TOOL_DESCRIPTIONS（关键！）

> ⚠️ **仅注册类是不够的**，必须将新工具的 Name 和 Description 添加到 `TOOL_DESCRIPTIONS` 字典中，否则 LLM 无法感知到该工具。

```python
# src/agents/tools.py
TOOL_DESCRIPTIONS = {
    "get_running_stats": {
        "description": "获取跑步统计数据...",
        "parameters": {...}
    },
    "my_new_tool": {  # ← 必须添加！
        "description": "工具描述，LLM会看到这段文字",
        "parameters": {
            "param1": "参数说明",
            "param2": "可选参数说明"
        }
    },
    ...
}
```

### 步骤 4：编写单元测试

```python
# tests/unit/agents/test_my_new_tool.py
import pytest
from src.agents.tools import MyNewTool

class TestMyNewTool:
    async def test_execute_success(self):
        tool = MyNewTool()
        result = await tool.execute(param1="test")
        assert result["success"] is True
        assert "data" in result
    
    async def test_execute_missing_required_param(self):
        tool = MyNewTool()
        result = await tool.execute()  # 缺少必需参数
        assert result["success"] is False
```

---

## 3. 工具返回格式规范

所有工具必须返回统一格式：

```python
# 成功
{
    "success": True,
    "data": {...}  # 实际数据
}

# 失败
{
    "success": False,
    "error": "错误信息",
    "details": "详细错误描述"  # 可选
}
```

---

## 4. 现有工具列表

| 工具名 | 功能 | 参数 |
|--------|------|------|
| `get_running_stats` | 获取跑步统计 | start_date, end_date |
| `get_recent_runs` | 获取最近记录 | limit |
| `calculate_vdot_for_run` | 计算单次 VDOT | distance_m, time_s |
| `get_vdot_trend` | 获取 VDOT 趋势 | limit |
| `get_hr_drift_analysis` | 心率漂移分析 | run_id |
| `get_training_load` | 获取训练负荷 | days |
| `query_by_date_range` | 按日期查询 | start_date, end_date |
| `query_by_distance` | 按距离查询 | min_distance, max_distance |
| `update_memory` | 更新记忆 | note, category |

---

## 5. 最佳实践

### 5.1 描述要清晰

```python
# ✅ 好的描述
description = "计算单次跑步的VDOT值（跑力值），使用Jack Daniels公式自动计算。注意：VDOT计算公式复杂，请使用此工具计算，不要自己用简单公式计算"

# ❌ 差的描述
description = "计算VDOT"
```

### 5.2 参数要有默认值

```python
# ✅ 好的参数定义
parameters = {
    "limit": {"type": "integer", "description": "返回数量限制（默认 10 条）"}
}

# 在 execute 中处理默认值
async def execute(self, **kwargs):
    limit = kwargs.get("limit", 10)
```

### 5.3 使用装饰器处理异常

```python
from src.core.decorators import handle_tool_errors

@handle_tool_errors(default_response={"success": False, "error": "操作失败"})
async def execute(self, **kwargs):
    # 业务逻辑
    ...
```

---

*文档版本: v1.0.0 | 更新日期: 2026-04-01*
