# 迭代开发任务清单 v0.2.0

## 📋 文档信息

| 项目 | 内容 |
|------|------|
| **版本号** | v0.2.0 |
| **迭代主题** | Agent 自然语言交互功能集成 |
| **迭代周期** | 2 周（10 个工作日） |
| **总预估工时** | 80 小时 |
| **任务总数** | 18 个 |
| **创建日期** | 2026-03-05 |
| **关联文档** | 《迭代需求规格说明书 v0.2.0》《迭代架构设计说明书 v0.2.0》 |

---

## 1. 任务分解总览

### 1.1 任务分类统计

| 任务类别 | 任务数量 | 总工时 (小时) | 占比 |
|---------|---------|--------------|------|
| 技术基础设施 | 4 | 20 | 25% |
| MVP 核心功能 | 8 | 40 | 50% |
| 测试与质量保障 | 4 | 14 | 17.5% |
| 文档与发布 | 2 | 6 | 7.5% |
| **总计** | **18** | **80** | **100%** |

### 1.2 迭代周期规划

| 迭代周期 | 时间 | 主要任务 | 交付物 |
|---------|------|---------|--------|
| **Sprint 1** | Week 1 | T001-T009 | Agent 框架 + 工具集 |
| **Sprint 2** | Week 2 | T010-T018 | 联调 + 测试 + 发布 |

### 1.3 任务依赖关系图

```mermaid
graph TD
    T001 --> T002
    T002 --> T003
    T003 --> T004
    T004 --> T005
    T005 --> T006
    T006 --> T007
    T007 --> T008
    T008 --> T009
    T009 --> T010
    T010 --> T011
    T011 --> T012
    T012 --> T013
    T013 --> T014
    T014 --> T015
    T015 --> T016
    T016 --> T017
    T017 --> T018
    
    style T001 fill:#e1f5ff
    style T009 fill:#fff4e1
    style T018 fill:#e8f5e9
```

---

## 2. 详细任务清单

### 2.1 技术基础设施（4 个任务，20 小时）

#### **T001 - 项目依赖配置与验证**

| 字段 | 内容 |
|------|------|
| **任务 ID** | T001 |
| **任务名称** | 项目依赖配置与验证 |
| **任务描述** | 确认 nanobot-ai 依赖版本，验证与现有依赖的兼容性，更新 pyproject.toml |
| **前置依赖** | 无 |
| **负责人** | 开发工程师 |
| **预估工时** | 4 小时 |
| **优先级** | P0 - 最高优先级 |
| **所属模块** | 项目配置 |
| **交付物** | 更新后的 pyproject.toml、依赖验证报告 |

**验收标准**:
- ✅ `pyproject.toml` 中 nanobot-ai 版本 >= 0.1.4
- ✅ 执行 `uv sync` 无依赖冲突
- ✅ 所有现有依赖保持兼容
- ✅ 能够成功导入 nanobot-ai 模块

**实施步骤**:
1. 检查当前 `pyproject.toml` 依赖配置
2. 确认 nanobot-ai 最低版本要求
3. 验证与其他依赖的兼容性
4. 更新依赖配置并执行同步
5. 编写依赖验证报告

**技术要点**:
- 使用 `uv pip compile` 检查依赖冲突
- 验证 Python 版本兼容性（>= 3.11）
- 记录所有依赖的版本号

---

#### **T002 - 开发环境搭建与验证**

| 字段 | 内容 |
|------|------|
| **任务 ID** | T002 |
| **任务名称** | 开发环境搭建与验证 |
| **任务描述** | 创建虚拟环境，安装所有依赖，验证开发工具链正常工作 |
| **前置依赖** | T001 |
| **负责人** | 开发工程师 |
| **预估工时** | 2 小时 |
| **优先级** | P0 - 最高优先级 |
| **所属模块** | 开发环境 |
| **交付物** | 可用的开发环境、环境验证脚本 |

**验收标准**:
- ✅ 虚拟环境创建成功
- ✅ 所有依赖安装完成
- ✅ `nanobotrun --help` 正常执行
- ✅ 测试框架可正常运行

**实施步骤**:
1. 创建/清理虚拟环境
2. 安装项目依赖（包括 dev 依赖）
3. 验证 CLI 命令正常
4. 运行单元测试验证环境
5. 编写环境验证脚本

**技术要点**:
- 使用 `uv venv` 创建虚拟环境
- 使用 `uv sync --all-extras` 安装依赖
- 验证 PowerShell 兼容性

---

#### **T003 - nanobot-ai 集成验证**

| 字段 | 内容 |
|------|------|
| **任务 ID** | T003 |
| **任务名称** | nanobot-ai 集成验证 |
| **任务描述** | 验证 nanobot-ai 基本功能，测试本地模型推理，确认工具调用机制 |
| **前置依赖** | T002 |
| **负责人** | 高级工程师 |
| **预估工时** | 8 小时 |
| **优先级** | P0 - 最高优先级 |
| **所属模块** | Agent 集成 |
| **交付物** | POC 验证代码、技术验证报告 |

**验收标准**:
- ✅ 能够成功实例化 NanobotAgent
- ✅ 本地模型推理正常工作
- ✅ 工具调用机制验证通过
- ✅ 无外部网络请求（隐私验证）
- ✅ 输出技术验证报告

**实施步骤**:
1. 阅读 nanobot-ai 官方文档
2. 创建简单的 POC 验证代码
3. 测试 Agent 初始化和工具注册
4. 验证本地模型推理能力
5. 使用网络监控工具验证无外部请求
6. 编写技术验证报告

**技术要点**:
- 使用 `local_model=True` 参数
- 配置简单的测试工具
- 使用 Wireshark 或类似工具监控网络

**风险与应对**:
- **风险**: nanobot-ai 兼容性问题
- **应对**: 准备备选方案（如其他本地 Agent 框架）

---

#### **T004 - 代码规范与质量门禁配置**

| 字段 | 内容 |
|------|------|
| **任务 ID** | T004 |
| **任务名称** | 代码规范与质量门禁配置 |
| **任务描述** | 配置 black、isort、mypy、bandit 等工具，确保代码质量 |
| **前置依赖** | T002 |
| **负责人** | 开发工程师 |
| **预估工时** | 6 小时 |
| **优先级** | P1 - 高优先级 |
| **所属模块** | 代码质量 |
| **交付物** | 配置文件、质量检查脚本 |

**验收标准**:
- ✅ black 配置完成并格式化现有代码
- ✅ isort 配置完成并排序导入
- ✅ mypy 类型检查配置完成
- ✅ bandit 安全扫描配置完成
- ✅ CI/CD 流水线集成质量检查

**实施步骤**:
1. 检查现有配置文件（pyproject.toml）
2. 配置 black 格式化工具
3. 配置 isort 导入排序
4. 配置 mypy 类型检查
5. 配置 bandit 安全扫描
6. 更新 CI/CD 配置文件

**技术要点**:
- 使用 `pyproject.toml` 统一配置
- 配置 pre-commit hooks（可选）
- 确保与现有 CI/CD 兼容

---

### 2.2 MVP 核心功能（8 个任务，40 小时）

#### **T005 - CLI chat 命令框架实现**

| 字段 | 内容 |
|------|------|
| **任务 ID** | T005 |
| **任务名称** | CLI chat 命令框架实现 |
| **任务描述** | 实现 `nanobotrun chat` 命令，包含 REPL 循环框架、欢迎界面、退出机制 |
| **前置依赖** | T003 |
| **负责人** | 中级工程师 |
| **预估工时** | 6 小时 |
| **优先级** | P0 - 最高优先级 |
| **所属模块** | CLI 交互 |
| **交付物** | src/cli.py（chat 函数）、单元测试 |

**验收标准**:
- ✅ 执行 `nanobotrun chat` 进入交互模式
- ✅ 显示欢迎界面和帮助提示
- ✅ 输入 `exit`/`quit`/`q` 正常退出
- ✅ 用户输入和系统回复有视觉区分
- ✅ 启动时间 < 1 秒
- ✅ 单元测试覆盖率 >= 80%

**实施步骤**:
1. 在 `src/cli.py` 中添加 `chat()` 命令
2. 实现 REPL 循环框架
3. 使用 Rich 库实现欢迎界面
4. 实现退出命令处理
5. 实现空输入处理
6. 实现异常处理
7. 编写单元测试

**技术要点**:
- 使用 `rich.prompt.Prompt` 获取用户输入
- 使用 `rich.console.Console` 显示输出
- 使用 `try-except` 处理异常
- 使用 `console.status()` 显示加载状态

**代码框架**:
```python
@app.command()
def chat():
    """启动自然语言交互模式"""
    console.print("[bold green]🤖 Nanobot Runner Agent[/bold green]")
    console.print("[dim]基于 nanobot-ai 的本地跑步数据助理[/dim]")
    console.print("=" * 60)
    
    while True:
        try:
            user_input = Prompt.ask("\n[bold cyan]您[/bold cyan]")
            if user_input.lower() in ["exit", "quit", "q"]:
                break
            # TODO: Agent 处理
        except Exception as e:
            console.print(f"[red]错误：{str(e)}[/red]")
```

---

#### **T006 - Agent 初始化与工具注册**

| 字段 | 内容 |
|------|------|
| **任务 ID** | T006 |
| **任务名称** | Agent 初始化与工具注册 |
| **任务描述** | 在 chat 命令中集成 nanobot-ai Agent，配置工具集和对话记忆 |
| **前置依赖** | T005 |
| **负责人** | 高级工程师 |
| **预估工时** | 8 小时 |
| **优先级** | P0 - 最高优先级 |
| **所属模块** | Agent 集成 |
| **交付物** | 集成代码、Agent 配置文档 |

**验收标准**:
- ✅ Agent 正确初始化
- ✅ RunnerTools 正确注册为工具集
- ✅ TOOL_DESCRIPTIONS 正确配置
- ✅ 对话记忆窗口设置为 10
- ✅ 使用本地模型推理

**实施步骤**:
1. 在 chat 命令中导入 NanobotAgent
2. 创建 RunnerTools 实例
3. 初始化 NanobotAgent 并配置参数
4. 配置工具描述
5. 配置对话记忆窗口
6. 测试 Agent 基本对话

**技术要点**:
- `memory_window=10` 保留最近 10 轮对话
- `local_model=True` 确保本地推理
- 工具描述要准确清晰

**代码框架**:
```python
from nanobot_ai import NanobotAgent
from src.agents.tools import RunnerTools, TOOL_DESCRIPTIONS

storage = StorageManager()
tools = RunnerTools(storage)

agent = NanobotAgent(
    tools=[tools],
    tool_descriptions=TOOL_DESCRIPTIONS,
    memory_window=10,
    local_model=True,
)
```

---

#### **T007 - query_by_date_range 工具实现**

| 字段 | 内容 |
|------|------|
| **任务 ID** | T007 |
| **任务名称** | query_by_date_range 工具实现 |
| **任务描述** | 实现按日期范围查询跑步记录的工具，使用 Polars Lazy API 优化性能 |
| **前置依赖** | T002 |
| **负责人** | 中级工程师 |
| **预估工时** | 6 小时 |
| **优先级** | P0 - 最高优先级 |
| **所属模块** | 工具集 |
| **交付物** | src/agents/tools.py（新增方法）、单元测试 |

**验收标准**:
- ✅ 支持精确日期查询
- ✅ 支持日期范围查询
- ✅ 返回结果按时间倒序排列
- ✅ 百万级数据量下查询响应 < 3 秒
- ✅ 使用 Polars Lazy API
- ✅ 单元测试覆盖率 >= 80%

**实施步骤**:
1. 在 `src/agents/tools.py` 中添加方法
2. 解析日期参数
3. 使用 Polars LazyFrame 查询
4. 实现日期范围过滤
5. 选择需要的列（列剪枝）
6. 排序并收集结果
7. 转换为字典列表
8. 编写单元测试

**技术要点**:
- 使用 `pl.scan_parquet()` 延迟加载
- 使用 `filter().select()` 链式调用
- 使用 `is_between()` 进行范围过滤
- 使用 `collect()` 触发执行

**代码框架**:
```python
def query_by_date_range(
    self,
    start_date: str,
    end_date: str
) -> List[Dict[str, Any]]:
    start_dt = datetime.strptime(start_date, "%Y-%m-%d")
    end_dt = datetime.strptime(end_date, "%Y-%m-%d")
    
    lf = self.storage.read_parquet()
    filtered_lf = lf.filter(
        pl.col("timestamp").is_between(start_dt, end_dt)
    ).select(["timestamp", "total_distance", ...])
    
    df = filtered_lf.sort("timestamp", descending=True).collect()
    
    results = []
    for row in df.iter_rows(named=True):
        results.append({...})
    
    return results
```

---

#### **T008 - query_by_distance 工具实现**

| 字段 | 内容 |
|------|------|
| **任务 ID** | T008 |
| **任务名称** | query_by_distance 工具实现 |
| **任务描述** | 实现按距离范围查询跑步记录的工具，支持单边界和双边界查询 |
| **前置依赖** | T007 |
| **负责人** | 中级工程师 |
| **预估工时** | 4 小时 |
| **优先级** | P0 - 最高优先级 |
| **所属模块** | 工具集 |
| **交付物** | src/agents/tools.py（新增方法）、单元测试 |

**验收标准**:
- ✅ 支持距离范围查询（如 5-10 公里）
- ✅ 支持单边界查询（如>10 公里）
- ✅ 返回结果包含关键指标
- ✅ 查询性能满足要求
- ✅ 单元测试覆盖率 >= 80%

**实施步骤**:
1. 在 `src/agents/tools.py` 中添加方法
2. 转换距离单位（公里转米）
3. 构建距离过滤条件
4. 使用 Polars LazyFrame 查询
5. 选择需要的列
6. 排序并收集结果
7. 编写单元测试

**技术要点**:
- 处理 `max_distance=None` 的情况
- 使用 `is_between()` 或 `>=` 操作符
- 注意单位转换（公里 -> 米）

**代码框架**:
```python
def query_by_distance(
    self,
    min_distance: float,
    max_distance: Optional[float] = None
) -> List[Dict[str, Any]]:
    min_meters = min_distance * 1000
    max_meters = max_distance * 1000 if max_distance else None
    
    lf = self.storage.read_parquet()
    
    if max_meters:
        distance_filter = pl.col("total_distance").is_between(min_meters, max_meters)
    else:
        distance_filter = pl.col("total_distance") >= min_meters
    
    filtered_lf = lf.filter(distance_filter).select([...])
    df = filtered_lf.sort("timestamp", descending=True).collect()
    
    return results
```

---

#### **T009 - 工具描述更新与注册**

| 字段 | 内容 |
|------|------|
| **任务 ID** | T009 |
| **任务名称** | 工具描述更新与注册 |
| **任务描述** | 更新 TOOL_DESCRIPTIONS 字典，添加新工具的准确描述 |
| **前置依赖** | T007, T008 |
| **负责人** | 开发工程师 |
| **预估工时** | 2 小时 |
| **优先级** | P0 - 最高优先级 |
| **所属模块** | 工具集 |
| **交付物** | 更新后的 TOOL_DESCRIPTIONS |

**验收标准**:
- ✅ query_by_date_range 描述准确
- ✅ query_by_distance 描述准确
- ✅ 参数类型和描述清晰
- ✅ 返回值描述完整
- ✅ Agent 能够正确理解工具

**实施步骤**:
1. 在 `src/agents/tools.py` 中找到 TOOL_DESCRIPTIONS
2. 添加 query_by_date_range 的描述
3. 添加 query_by_distance 的描述
4. 验证描述准确性
5. 测试 Agent 工具调用

**技术要点**:
- 描述要简洁清晰
- 参数说明要包含格式要求
- 提供使用示例

**更新内容**:
```python
TOOL_DESCRIPTIONS = {
    # ... 原有工具描述 ...
    
    "query_by_date_range": {
        "description": "按日期范围查询跑步记录",
        "parameters": {
            "start_date": "开始日期（格式：YYYY-MM-DD）",
            "end_date": "结束日期（格式：YYYY-MM-DD）",
        },
        "returns": "跑步记录列表，包含时间、距离、用时、心率等",
    },
    "query_by_distance": {
        "description": "按距离范围查询跑步记录",
        "parameters": {
            "min_distance": "最小距离（公里）",
            "max_distance": "最大距离（公里，可选）",
        },
        "returns": "跑步记录列表，包含时间、距离、用时、心率等",
    },
}
```

---

#### **T010 - Agent 自然语言理解集成**

| 字段 | 内容 |
|------|------|
| **任务 ID** | T010 |
| **任务名称** | Agent 自然语言理解集成 |
| **任务描述** | 实现 Agent 与 chat 命令的完整集成，测试自然语言理解和工具调用 |
| **前置依赖** | T006, T009 |
| **负责人** | 高级工程师 |
| **预估工时** | 8 小时 |
| **优先级** | P0 - 最高优先级 |
| **所属模块** | Agent 集成 |
| **交付物** | 集成代码、测试用例 |

**验收标准**:
- ✅ Agent 能够理解用户自然语言提问
- ✅ 正确调用对应工具
- ✅ 工具调用准确率 >= 95%
- ✅ 多轮对话保持上下文
- ✅ 意图识别准确率 >= 90%

**实施步骤**:
1. 在 chat 命令中调用 agent.chat()
2. 测试各类用户问题
3. 验证工具调用正确性
4. 测试多轮对话上下文
5. 记录意图识别准确率
6. 优化 Prompt（如需要）

**技术要点**:
- 使用 `agent.chat(user_input)` 进行对话
- 测试时间表达（上周、上个月等）
- 测试距离表达（10 公里、半马等）
- 测试指标表达（跑力值、心率漂移等）

**测试用例**:
```python
# 测试场景 1：统计数据查询
response = agent.chat("我总共跑了多少次？")
assert "次" in response

# 测试场景 2：趋势分析
response = agent.chat("我的跑力值最近有提升吗？")
assert "VDOT" in response or "跑力" in response

# 测试场景 3：范围查询
response = agent.chat("我上周跑了多少次？")
assert isinstance(response, str)
```

---

#### **T011 - Rich 格式化输出实现**

| 字段 | 内容 |
|------|------|
| **任务 ID** | T011 |
| **任务名称** | Rich 格式化输出实现 |
| **任务描述** | 使用 Rich 库格式化 Agent 回复，包括表格、面板、关键指标高亮 |
| **前置依赖** | T010 |
| **负责人** | 中级工程师 |
| **预估工时** | 6 小时 |
| **优先级** | P1 - 高优先级 |
| **所属模块** | CLI 交互 |
| **交付物** | 格式化输出代码、UI 示例截图 |

**验收标准**:
- ✅ 数据表格格式正确、对齐
- ✅ 关键指标使用颜色高亮
- ✅ 回复包含数据洞察和建议
- ✅ 无数据时提供友好提示
- ✅ 响应时间 < 2 秒（不含工具调用）

**实施步骤**:
1. 创建格式化输出辅助函数
2. 实现表格展示函数
3. 实现面板展示函数
4. 实现关键指标高亮
5. 集成到 Agent 回复流程
6. 测试各类输出场景

**技术要点**:
- 使用 `rich.table.Table` 展示表格
- 使用 `rich.panel.Panel` 展示面板
- 使用 `rich.text.Text` 格式化文本
- 使用颜色样式突出重要信息

**代码框架**:
```python
from rich.table import Table
from rich.panel import Panel

def format_runs_table(runs: List[Dict[str, Any]]) -> Table:
    table = Table(title="最近跑步记录", header_style="bold magenta")
    table.add_column("日期", style="cyan")
    table.add_column("距离", style="green")
    # ... 添加其他列
    
    for run in runs:
        table.add_row(...)
    
    return table

def format_stats_panel(stats: Dict[str, Any]) -> Panel:
    text = Text()
    text.append("📊 跑步统计\n\n", style="bold magenta")
    text.append("总次数：", style="cyan")
    text.append(f"{stats['total_runs']} 次\n", style="bold green")
    # ...
    return Panel(text, border_style="green")
```

---

#### **T012 - 错误处理与边界情况**

| 字段 | 内容 |
|------|------|
| **任务 ID** | T012 |
| **任务名称** | 错误处理与边界情况 |
| **任务描述** | 实现完整的错误处理机制，处理空数据库、参数错误、工具调用失败等场景 |
| **前置依赖** | T010 |
| **负责人** | 中级工程师 |
| **预估工时** | 6 小时 |
| **优先级** | P0 - 最高优先级 |
| **所属模块** | 错误处理 |
| **交付物** | 错误处理代码、异常测试用例 |

**验收标准**:
- ✅ 所有异常场景有对应的错误处理
- ✅ 错误提示友好且具有指导性
- ✅ 无系统崩溃或未捕获异常
- ✅ 错误日志完整记录
- ✅ 异常测试用例覆盖所有场景

**实施步骤**:
1. 创建错误处理装饰器
2. 实现空数据库处理
3. 实现参数错误处理
4. 实现工具调用失败处理
5. 实现意图不明处理
6. 编写异常测试用例

**技术要点**:
- 使用装饰器统一处理异常
- 使用 logging 记录详细日志
- 提供友好的用户提示
- 区分系统异常和业务异常

**代码框架**:
```python
from functools import wraps

def handle_agent_errors(default_response: str = "抱歉，暂时无法完成此操作"):
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except FileNotFoundError:
                return "暂无数据，请先使用 import 命令导入跑步数据"
            except ValueError as e:
                return f"参数错误：{str(e)}"
            except Exception as e:
                logging.error(f"工具调用失败：{e}", exc_info=True)
                return default_response
        return wrapper
    return decorator
```

**测试场景**:
- 空数据库场景
- 日期格式错误
- 距离范围无效
- 查询结果为空
- 工具调用失败

---

### 2.3 测试与质量保障（4 个任务，14 小时）

#### **T013 - 单元测试编写**

| 字段 | 内容 |
|------|------|
| **任务 ID** | T013 |
| **任务名称** | 单元测试编写 |
| **任务描述** | 为所有新增功能编写单元测试，确保代码覆盖率 >= 80% |
| **前置依赖** | T007, T008, T011, T012 |
| **负责人** | 测试工程师 |
| **预估工时** | 8 小时 |
| **优先级** | P0 - 最高优先级 |
| **所属模块** | 测试 |
| **交付物** | 测试文件、覆盖率报告 |

**验收标准**:
- ✅ 单元测试覆盖率 >= 80%
- ✅ 所有测试用例通过
- ✅ 测试代码符合规范
- ✅ 测试报告生成成功

**实施步骤**:
1. 创建测试文件 `tests/unit/test_agent_integration.py`
2. 编写 query_by_date_range 测试
3. 编写 query_by_distance 测试
4. 编写格式化输出测试
5. 编写错误处理测试
6. 执行测试并生成覆盖率报告

**技术要点**:
- 使用 pytest 框架
- 使用 pytest-cov 生成覆盖率报告
- 使用 mock 模拟外部依赖
- 测试正常场景和异常场景

**测试文件结构**:
```python
# tests/unit/test_agent_integration.py

def test_query_by_date_range():
    """测试日期范围查询"""
    tools = RunnerTools()
    result = tools.query_by_date_range("2026-01-01", "2026-03-05")
    assert isinstance(result, list)
    assert all("timestamp" in r for r in result)

def test_query_by_distance():
    """测试距离范围查询"""
    tools = RunnerTools()
    result = tools.query_by_distance(min_distance=10, max_distance=20)
    assert isinstance(result, list)
    assert all(r["distance"] >= 10 for r in result)

def test_empty_database():
    """测试空数据库处理"""
    tools = RunnerTools()
    result = tools.get_running_stats()
    assert result == {"message": "暂无跑步数据"}

def test_format_runs_table():
    """测试表格格式化"""
    runs = [...]
    table = format_runs_table(runs)
    assert isinstance(table, Table)
```

---

#### **T014 - 集成测试编写**

| 字段 | 内容 |
|------|------|
| **任务 ID** | T014 |
| **任务名称** | 集成测试编写 |
| **任务描述** | 编写 Agent 交互集成测试，验证完整流程 |
| **前置依赖** | T013 |
| **负责人** | 测试工程师 |
| **预估工时** | 4 小时 |
| **优先级** | P0 - 最高优先级 |
| **所属模块** | 测试 |
| **交付物** | 集成测试文件、测试报告 |

**验收标准**:
- ✅ 集成测试覆盖所有核心场景
- ✅ 所有测试用例通过
- ✅ 测试报告完整
- ✅ 无阻塞性缺陷

**实施步骤**:
1. 创建测试文件 `tests/integration/test_agent_chat.py`
2. 编写启动测试
3. 编写对话测试
4. 编写多轮对话测试
5. 执行集成测试

**技术要点**:
- 使用 pytest 框架
- 模拟用户输入
- 验证 Agent 回复
- 测试上下文保持

**测试文件结构**:
```python
# tests/integration/test_agent_chat.py

def test_agent_chat_basic():
    """测试基本对话"""
    agent = create_test_agent()
    response = agent.chat("我总共跑了多少次？")
    assert isinstance(response, str)
    assert len(response) > 0

def test_agent_chat_context():
    """测试多轮对话"""
    agent = create_test_agent()
    response1 = agent.chat("我上周跑了多少次？")
    response2 = agent.chat("那这个月呢？")
    assert isinstance(response1, str)
    assert isinstance(response2, str)

def test_agent_chat_tool_calling():
    """测试工具调用"""
    agent = create_test_agent()
    response = agent.chat("查询我最近 10 公里的跑步")
    assert isinstance(response, str)
```

---

#### **T015 - 性能基准测试**

| 字段 | 内容 |
|------|------|
| **任务 ID** | T015 |
| **任务名称** | 性能基准测试 |
| **任务描述** | 执行性能基准测试，验证所有性能指标达标 |
| **前置依赖** | T013 |
| **负责人** | 测试工程师 |
| **预估工时** | 4 小时 |
| **优先级** | P1 - 高优先级 |
| **所属模块** | 性能测试 |
| **交付物** | 性能测试报告、优化建议 |

**验收标准**:
- ✅ CLI 启动时间 < 1 秒
- ✅ 简单查询响应 < 1 秒
- ✅ 复杂查询响应 < 3 秒
- ✅ 内存占用 < 500MB
- ✅ 提供性能测试报告

**实施步骤**:
1. 创建测试文件 `tests/performance/test_query_performance.py`
2. 编写启动时间测试
3. 编写查询性能测试
4. 编写内存占用测试
5. 执行性能测试
6. 生成性能报告

**技术要点**:
- 使用 pytest-benchmark 或 time 模块
- 使用 psutil 监控内存
- 测试不同数据规模
- 记录详细性能数据

**测试文件结构**:
```python
# tests/performance/test_query_performance.py

import time
import psutil
import os

def test_cli_startup_time():
    """测试 CLI 启动时间"""
    start = time.time()
    # 启动 CLI
    elapsed = time.time() - start
    assert elapsed < 1.0, f"启动时间 {elapsed}s 超过 1s 要求"

def test_query_performance_large_dataset():
    """测试大数据集查询性能"""
    tools = RunnerTools()
    
    start = time.time()
    result = tools.query_by_date_range("2024-01-01", "2026-12-31")
    elapsed = time.time() - start
    
    assert elapsed < 3.0, f"查询耗时 {elapsed}s 超过 3s 要求"

def test_memory_usage():
    """测试内存占用"""
    process = psutil.Process(os.getpid())
    memory = process.memory_info().rss / 1024 / 1024  # MB
    assert memory < 500, f"内存占用 {memory}MB 超过 500MB 要求"
```

---

#### **T016 - 代码质量检查与优化**

| 字段 | 内容 |
|------|------|
| **任务 ID** | T016 |
| **任务名称** | 代码质量检查与优化 |
| **任务描述** | 执行代码质量检查（black、isort、mypy、bandit），修复所有问题 |
| **前置依赖** | T013 |
| **负责人** | 高级工程师 |
| **预估工时** | 6 小时 |
| **优先级** | P0 - 最高优先级 |
| **所属模块** | 代码质量 |
| **交付物** | 质量检查报告、修复记录 |

**验收标准**:
- ✅ black 格式化检查通过
- ✅ isort 导入排序检查通过
- ✅ mypy 类型检查通过
- ✅ bandit 安全扫描无高危漏洞
- ✅ 所有质量问题已修复

**实施步骤**:
1. 执行 black 格式化检查
2. 执行 isort 导入排序检查
3. 执行 mypy 类型检查
4. 执行 bandit 安全扫描
5. 修复所有发现的问题
6. 生成质量检查报告

**技术要点**:
- 使用 `python -m black --check src/ tests/`
- 使用 `python -m isort --check-only src/ tests/`
- 使用 `python -m mypy src/`
- 使用 `python -m bandit -r src/`

**检查命令**:
```bash
# 格式化检查
python -m black --check src/ tests/
python -m isort --check-only src/ tests/

# 类型检查
python -m mypy src/

# 安全扫描
python -m bandit -r src/
```

---

### 2.4 文档与发布（2 个任务，6 小时）

#### **T017 - 用户文档更新**

| 字段 | 内容 |
|------|------|
| **任务 ID** | T017 |
| **任务名称** | 用户文档更新 |
| **任务描述** | 更新用户手册、README、帮助文档，添加 chat 命令使用说明 |
| **前置依赖** | T010, T011 |
| **负责人** | 技术文档工程师 |
| **预估工时** | 4 小时 |
| **优先级** | P1 - 高优先级 |
| **所属模块** | 文档 |
| **交付物** | 更新后的 README.md、用户手册 |

**验收标准**:
- ✅ README.md 包含 chat 命令说明
- ✅ 用户手册包含完整使用指南
- ✅ 帮助文档包含示例问题
- ✅ 文档清晰易懂

**实施步骤**:
1. 更新 README.md 添加 chat 命令
2. 更新用户手册
3. 添加使用示例
4. 添加常见问题 FAQ
5. 审查文档质量

**技术要点**:
- 提供清晰的命令格式
- 提供丰富的使用示例
- 添加常见问题解答
- 使用 Markdown 格式

**更新内容**:
```markdown
## 自然语言交互

启动 Agent 交互模式：

```bash
nanobotrun chat
```

示例问题：
- "我总共跑了多少次？"
- "我上周跑了多少公里？"
- "我的跑力值最近有提升吗？"
- "查询我最近 10 公里的跑步"
```

---

#### **T018 - 版本发布准备**

| 字段 | 内容 |
|------|------|
| **任务 ID** | T018 |
| **任务名称** | 版本发布准备 |
| **任务描述** | 准备 v0.2.0 版本发布，包括版本号更新、发布说明、Tag 创建 |
| **前置依赖** | T016, T017 |
| **负责人** | 发布经理 |
| **预估工时** | 2 小时 |
| **优先级** | P0 - 最高优先级 |
| **所属模块** | 发布 |
| **交付物** | 发布说明、版本 Tag、发布报告 |

**验收标准**:
- ✅ 版本号更新为 0.2.0
- ✅ 发布说明完整
- ✅ 版本 Tag 创建成功
- ✅ CI/CD 流水线触发成功
- ✅ 发布报告生成

**实施步骤**:
1. 更新 pyproject.toml 版本号
2. 编写发布说明（CHANGELOG.md）
3. 创建 git commit
4. 创建并推送版本 Tag
5. 触发 CI/CD 流水线
6. 生成发布报告

**技术要点**:
- 使用语义化版本号（v0.2.0）
- 发布说明包含所有变更
- Tag 格式规范（v0.2.0）

**发布说明模板**:
```markdown
# v0.2.0 发布说明

## 新增功能
- ✨ 实现 Agent 自然语言交互功能
- ✨ 新增 query_by_date_range 工具
- ✨ 新增 query_by_distance 工具
- ✨ 实现 Rich 格式化输出

## 技术改进
- 🚀 使用 Polars Lazy API 优化查询性能
- 🔒 增强错误处理机制
- 📝 完善单元测试和集成测试

## 已知问题
- 无

## 升级指南
执行以下命令升级：
```bash
uv sync
```
```

---

## 3. 任务依赖关系矩阵

### 3.1 前置依赖关系表

| 任务 ID | 任务名称 | 前置任务 | 后续任务 |
|--------|---------|---------|---------|
| T001 | 项目依赖配置与验证 | - | T002 |
| T002 | 开发环境搭建与验证 | T001 | T003, T004, T005, T007 |
| T003 | nanobot-ai 集成验证 | T002 | T005 |
| T004 | 代码规范与质量门禁配置 | T002 | - |
| T005 | CLI chat 命令框架实现 | T002, T003 | T006 |
| T006 | Agent 初始化与工具注册 | T005 | T010 |
| T007 | query_by_date_range 工具实现 | T002 | T009 |
| T008 | query_by_distance 工具实现 | T007 | T009 |
| T009 | 工具描述更新与注册 | T007, T008 | T010 |
| T010 | Agent 自然语言理解集成 | T006, T009 | T011, T012 |
| T011 | Rich 格式化输出实现 | T010 | T017 |
| T012 | 错误处理与边界情况 | T010 | T013 |
| T013 | 单元测试编写 | T012 | T014, T015, T016 |
| T014 | 集成测试编写 | T013 | - |
| T015 | 性能基准测试 | T013 | - |
| T016 | 代码质量检查与优化 | T013 | T018 |
| T017 | 用户文档更新 | T010, T011 | T018 |
| T018 | 版本发布准备 | T016, T017 | - |

### 3.2 关键路径分析

**关键路径**（最长依赖链）:
```
T001 → T002 → T003 → T005 → T006 → T009 → T010 → T012 → T013 → T016 → T018
```

**关键路径总工时**: 4+2+8+6+8+2+8+6+8+6+2 = **60 小时**

**并行任务**:
- T004（代码规范配置）可与 T003-T012 并行
- T007-T008（工具实现）可与 T005-T006 并行
- T014-T015（测试编写）可与 T016 并行
- T017（文档更新）可与 T016 并行

---

## 4. 迭代计划

### 4.1 Sprint 1（Week 1）

| 日期 | 任务 | 负责人 | 工时 | 交付物 |
|------|------|--------|------|--------|
| Day 1 | T001, T002 | 开发工程师 | 6h | 开发环境就绪 |
| Day 2 | T003 | 高级工程师 | 8h | POC 验证代码 |
| Day 3 | T005, T006 | 中级工程师 | 8h | chat 命令框架 |
| Day 4 | T007, T008 | 中级工程师 | 8h | 查询工具实现 |
| Day 5 | T009, T010 | 高级工程师 | 8h | Agent 集成完成 |

**Sprint 1 里程碑**:
- ✅ 开发环境搭建完成
- ✅ nanobot-ai 集成验证通过
- ✅ chat 命令可运行
- ✅ 工具集完整实现
- ✅ Agent 能够调用工具

---

### 4.2 Sprint 2（Week 2）

| 日期 | 任务 | 负责人 | 工时 | 交付物 |
|------|------|--------|------|--------|
| Day 6 | T011, T012 | 中级工程师 | 8h | 格式化输出 + 错误处理 |
| Day 7 | T013 | 测试工程师 | 8h | 单元测试完成 |
| Day 8 | T014, T015 | 测试工程师 | 8h | 集成测试 + 性能测试 |
| Day 9 | T016, T017 | 高级工程师 | 8h | 质量检查 + 文档更新 |
| Day 10 | T018 | 发布经理 | 2h | 版本发布 |

**Sprint 2 里程碑**:
- ✅ 所有功能开发完成
- ✅ 单元测试覆盖率 >= 80%
- ✅ 集成测试通过
- ✅ 性能指标达标
- ✅ 代码质量检查通过
- ✅ v0.2.0 正式发布

---

## 5. 风险管理

### 5.1 技术风险

| 风险项 | 可能性 | 影响 | 应对策略 | 负责人 |
|--------|--------|------|---------|--------|
| nanobot-ai 兼容性 | 中 | 高 | 提前验证，准备备选方案 | 高级工程师 |
| 性能不达标 | 中 | 高 | Polars Lazy API 优化，添加缓存 | 中级工程师 |
| 意图识别准确率低 | 高 | 中 | 提供示例问题引导，优化 Prompt | 高级工程师 |
| 大数据量查询慢 | 中 | 高 | 添加索引，优化查询策略 | 中级工程师 |

### 5.2 项目风险

| 风险项 | 可能性 | 影响 | 应对策略 | 负责人 |
|--------|--------|------|---------|--------|
| 开发周期延期 | 中 | 中 | 优先保证 MVP，扩展功能延后 | 项目经理 |
| 测试覆盖不足 | 高 | 中 | 制定详细测试计划，自动化测试 | 测试工程师 |
| 文档不完整 | 中 | 低 | 文档与代码同步开发 | 文档工程师 |

---

## 6. 验收标准汇总

### 6.1 功能验收

| 功能项 | 验收方法 | 状态 |
|--------|---------|------|
| Agent 交互入口 | 手动测试 + 自动化测试 | 待验收 |
| nanobot-ai 集成 | 代码审查 + 功能测试 | 待验收 |
| 数据查询工具集 | 单元测试 + 集成测试 | 待验收 |
| 自然语言理解 | 场景测试 + 准确率验证 | 待验收 |
| 响应生成与格式化 | 手动测试 + UI 审查 | 待验收 |
| 错误处理 | 异常测试 + 边界测试 | 待验收 |

### 6.2 性能验收

| 测试场景 | 数据规模 | 响应时间要求 | 实测结果 | 状态 |
|---------|---------|-------------|---------|------|
| 启动 CLI | - | < 1s | 待测试 | 待验收 |
| 简单查询 | 1 万条记录 | < 1s | 待测试 | 待验收 |
| 复杂查询 | 10 万条记录 | < 3s | 待测试 | 待验收 |
| 心率漂移分析 | 100 万条记录 | < 3s | 待测试 | 待验收 |

### 6.3 质量验收

| 指标 | 要求 | 测量工具 | 状态 |
|------|------|---------|------|
| 单元测试覆盖率 | >= 80% | pytest-cov | 待测试 |
| 类型检查通过率 | 100% | mypy | 待测试 |
| 代码格式化 | 100% | black, isort | 待测试 |
| 安全扫描 | 无高危漏洞 | bandit | 待测试 |
| 意图识别准确率 | >= 90% | 测试集验证 | 待测试 |
| 工具调用准确率 | >= 95% | 测试集验证 | 待测试 |

---

## 7. 附录

### 7.1 任务优先级定义

| 优先级 | 说明 | 处理策略 |
|--------|------|---------|
| **P0** | 最高优先级，MVP 核心功能 | 必须完成，否则无法发布 |
| **P1** | 高优先级，重要功能 | 应该完成，可少量延期 |
| **P2** | 中优先级，增强功能 | 可以延期到下一迭代 |

### 7.2 工时评估方法

**三点估算法**:
- **乐观时间** (O): 最佳情况下的工时
- **最可能时间** (M): 正常情况下的工时
- **悲观时间** (P): 最差情况下的工时
- **预估工时** = (O + 4M + P) / 6

**误差控制**:
- 预估工时误差控制在 ±20% 以内
- 复杂任务由高级工程师复核
- 考虑风险缓冲时间（10-20%）

### 7.3 任务状态定义

| 状态 | 说明 | 流转规则 |
|------|------|---------|
| **待开始** | 任务未开始 | 前置任务完成后流转 |
| **进行中** | 任务正在执行 | 负责人开始工作时更新 |
| **已完成** | 任务完成并通过验收 | 验收通过后更新 |
| **已阻塞** | 任务因依赖问题阻塞 | 发现问题时更新 |

---

**文档状态**: 待评审  
**下次更新**: 迭代开始后每日更新进度  
**发布版本**: v0.2.0

**审批记录**:
- [ ] 架构师评审
- [ ] 技术负责人评审
- [ ] 项目经理审批

---

## 8. 任务进度跟踪表

### 8.1 每日站会更新模板

```markdown
## 日期：YYYY-MM-DD

### 完成任务
- [任务 ID] 任务名称 - 负责人 - 状态

### 进行中任务
- [任务 ID] 任务名称 - 负责人 - 进度% - 预计完成时间

### 阻塞任务
- [任务 ID] 任务名称 - 负责人 - 阻塞原因 - 需要协助

### 风险与问题
- 风险描述 - 影响 - 建议措施
```

### 8.2 迭代燃尽图数据

| 日期 | 剩余工时 | 完成任务数 | 备注 |
|------|---------|-----------|------|
| Day 0 | 80h | 0 | 迭代开始 |
| Day 1 | - | - | - |
| Day 2 | - | - | - |
| ... | - | - | - |
| Day 10 | 0h | 18 | 迭代结束 |

---

**文档结束**