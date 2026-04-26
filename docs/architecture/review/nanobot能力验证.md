我先扫描项目结构，了解整体代码组织，然后分析对外提供的SDK功能。


        
            
toolName: view_folder
            
status: success
          
d:\yecll\Documents\GitHub\nanobot
          

        
            
toolName: view_files
            
status: success
          
            
filePath: d:\yecll\Documents\GitHub\nanobot\nanobot\__init__.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: d:\yecll\Documents\GitHub\nanobot\nanobot\nanobot.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: d:\yecll\Documents\GitHub\nanobot\docs\python-sdk.md
          

        
            
toolName: view_files
            
status: success
          
            
filePath: d:\yecll\Documents\GitHub\nanobot\pyproject.toml
          

        
            
toolName: view_files
            
status: success
          
            
filePath: d:\yecll\Documents\GitHub\nanobot\nanobot\agent\hook.py
          

        
            
toolName: view_files
            
status: success
          
            
filePath: d:\yecll\Documents\GitHub\nanobot\nanobot\agent\__init__.py
          
## nanobot 作为 Python SDK 对外提供的功能分析

### 一、核心入口

项目通过 `nanobot` 包名对外暴露，主要入口在 [nanobot/__init__.py](file:///d:/yecll/Documents/GitHub/nanobot/nanobot/__init__.py):

```python
from nanobot.nanobot import Nanobot, RunResult

__all__ = ["Nanobot", "RunResult"]
```

### 二、SDK 对外功能清单

| 功能类别 | 对外 API | 说明 |
|---------|---------|------|
| **Agent 执行** | `Nanobot.from_config()` | 从配置文件创建 Agent 实例，支持指定 config 路径和工作目录 |
| **单次推理** | `await bot.run(message)` | 向 Agent 发送消息并获取回复，返回 `RunResult` |
| **会话隔离** | `session_key` 参数 | 不同 session_key 拥有独立的对话历史 |
| **生命周期钩子** | `AgentHook` 基类 | 可观察/定制 Agent 运行各阶段行为 |
| **流式输出** | `on_stream()` 回调 | 支持 token-by-token 的流式响应接收 |
| **内容后处理** | `finalize_content()` | 可对最终输出内容进行管道式转换 |

### 三、核心类详细说明

#### 1. `Nanobot` — 主 Facade 类

```python
class Nanobot:
    @classmethod
    def from_config(
        cls,
        config_path: str | Path | None = None,
        *,
        workspace: str | Path | None = None,
    ) -> Nanobot

    async def run(
        self,
        message: str,
        *,
        session_key: str = "sdk:default",
        hooks: list[AgentHook] | None = None,
    ) -> RunResult
```

#### 2. `RunResult` — 运行结果

```python
@dataclass
class RunResult:
    content: str          # Agent 最终文本回复
    tools_used: list[str] # 使用的工具列表（预留）
    messages: list[dict]  # 完整消息历史（预留）
```

#### 3. `AgentHook` — 生命周期钩子

```python
class AgentHook:
    def wants_streaming() -> bool                    # 是否启用流式
    async def before_iteration(context)              # 每次 LLM 调用前
    async def on_stream(context, delta)              # 流式 token 回调
    async def on_stream_end(context, resuming)       # 流式结束
    async def before_execute_tools(context)          # 工具执行前
    async def after_iteration(context)               # 每次迭代后
    def finalize_content(context, content) -> str    # 最终内容转换
```

#### 4. `AgentHookContext` — 钩子上下文

```python
@dataclass
class AgentHookContext:
    iteration: int              # 当前迭代次数
    messages: list[dict]        # 消息历史
    response: LLMResponse       # LLM 响应
    usage: dict[str, int]       # Token 用量
    tool_calls: list[ToolCallRequest]  # 工具调用列表
    tool_results: list[Any]     # 工具执行结果
    tool_events: list[dict]     # 工具事件
    final_content: str | None   # 最终内容
    stop_reason: str | None     # 停止原因
    error: str | None           # 错误信息
```

### 四、`nanobot.agent` 子模块导出

[nanobot/agent/__init__.py](file:///d:/yecll/Documents/GitHub/nanobot/nanobot/agent/__init__.py) 额外导出了以下类（供高级用户扩展使用）：

| 导出类 | 用途 |
|-------|------|
| `ContextBuilder` | 构建 Agent 上下文 |
| `AgentLoop` | Agent 核心运行循环 |
| `CompositeHook` | 组合多个钩子的扇出钩子 |
| `Dream` | 梦境/记忆存储模型 |
| `MemoryStore` | 记忆存储管理 |
| `SkillsLoader` | 技能加载器 |
| `SubagentManager` | 子 Agent 管理器 |

### 五、典型使用场景

```python
import asyncio
from nanobot import Nanobot
from nanobot.agent import AgentHook, AgentHookContext

class AuditHook(AgentHook):
    def wants_streaming(self) -> bool:
        return True

    async def on_stream(self, context: AgentHookContext, delta: str) -> None:
        print(delta, end="", flush=True)

    async def before_execute_tools(self, context: AgentHookContext) -> None:
        for tc in context.tool_calls:
            print(f"\n[tool] {tc.name}")

async def main():
    bot = Nanobot.from_config(workspace="/my/project")
    
    # 独立会话
    result1 = await bot.run("分析这个项目", session_key="user-a")
    result2 = await bot.run("总结代码", session_key="user-b")
    
    # 带钩子
    result = await bot.run("解释架构", hooks=[AuditHook()])
    print(result.content)

asyncio.run(main())
```

### 六、总结

nanobot 作为 Python SDK，对外提供的是一个**轻量级 AI Agent 编程接口**：

- **核心能力**：通过 `Nanobot.run()` 向 AI Agent 发送指令并获取回复
- **会话管理**：通过 `session_key` 实现多用户/多任务对话隔离
- **可观测性**：通过 `AgentHook` 体系观察工具调用、流式输出、迭代状态
- **可扩展性**：可自定义钩子实现审计、监控、内容过滤等需求
- **配置复用**：直接复用 CLI 的 `~/.nanobot/config.json` 配置