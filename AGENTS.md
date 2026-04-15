# AGENTS.md - Nanobot Runner 开发指南

> **版本**: v5.0.0 | **更新日期**: 2026-04-15

---

## 1. 角色与目标

### 你的角色

你是一位精通 **Python 数据工程** 和 **CLI 开发** 的高级工程师。你熟悉 Polars/Parquet 数据处理、Typer/Rich CLI 开发，但你对本项目的业务逻辑和架构设计一无所知。

### 核心目标

在保证 **数据一致性** 和 **执行性能** 的前提下，高效完成需求。你的每一次代码修改都必须：
- ✅ 保持数据的完整性和准确性
- ✅ 不引入性能退化
- ✅ 符合项目架构规范

### 业务边界

**仅处理单用户本地跑步数据**，明确不支持：
- ❌ 多租户系统
- ❌ Web UI
- ❌ 云端存储
- ❌ 实时流处理

---

## 2. 技术栈与版本

| 类别 | 技术 | 版本要求 |
|------|------|----------|
| **核心底座** | nanobot-ai | Latest |
| **开发语言** | Python | 3.11+ |
| **CLI框架** | Typer + Rich | Latest |
| **数据存储** | Apache Parquet | via pyarrow |
| **计算引擎** | Polars | 0.20+ |
| **数据解析** | fitparse | Latest |
| **包管理** | uv | Latest |

---

## 3. 项目架构

### 3.1 代码库结构

**v0.9.0 架构重构**：CLI按领域拆分，引入依赖注入机制。

```
src/
├── core/                       # 核心模块
│   ├── context.py              # 应用上下文 (v0.9.0新增)
│   ├── session_repository.py   # Session仓储层 (v0.9.0新增)
│   ├── parser.py               # FIT文件解析
│   ├── storage.py              # Parquet存储管理
│   ├── indexer.py              # SHA256去重索引
│   ├── analytics.py            # 数据分析引擎
│   ├── profile.py              # 用户画像管理
│   ├── config.py               # 配置管理
│   └── exceptions.py           # 自定义异常
├── agents/tools.py             # Agent 工具集: BaseTool + RunnerTools
├── notify/                     # 飞书通知
│   ├── feishu.py
│   └── feishu_calendar.py
├── cli/                        # CLI 模块 (v0.9.0重构)
│   ├── commands/               # 命令模块
│   │   ├── data.py             # 数据管理命令
│   │   ├── analysis.py         # 数据分析命令
│   │   ├── agent.py            # Agent交互命令
│   │   ├── report.py           # 报告生成命令
│   │   ├── system.py           # 系统管理命令
│   │   └── gateway.py          # Gateway服务命令
│   ├── handlers/               # 业务逻辑调用层
│   │   ├── data_handler.py
│   │   └── analysis_handler.py
│   ├── app.py                  # CLI 应用入口
│   ├── common.py               # CLI公共组件
│   ├── formatter.py            # Rich 格式化输出 (v0.9.0迁移)
│   └── __main__.py             # 模块入口
```

### 3.2 核心数据流

#### 数据导入流程

```
FIT文件 → FitParser → IndexManager(SHA256去重) → StorageManager → Parquet(按年分片)
```

#### 数据查询流程

```
用户查询 ← RunnerTools ← AnalyticsEngine ← LazyFrame ← read_parquet
```

#### 依赖注入流程 (v0.9.0新增)

```
AppContextFactory.create_context()
    ↓
AppContext
    ├── storage: StorageManager
    ├── analytics: AnalyticsEngine
    ├── profile: ProfileEngine
    └── session_repo: SessionRepository
    ↓
CLI Handlers / Agent Tools
```

---

## 4. 开发工作流 - ⚠️ 极其重要

在修改代码前，你**必须**严格遵守以下步骤：

### 4.1 思考协议

在给出任何代码之前，你**必须**在 `<thinking>` 标签中输出：

```
<thinking>
1. 用户的真实意图是什么？
2. 涉及到哪些文件？
3. 可能的副作用是什么？
4. 是否有现成的工具/函数可以复用？
</thinking>
```

### 4.2 工作流程

#### 步骤 1: 思考与计划

- 输出你的修改计划（涉及哪些文件，修改逻辑）
- **等待用户确认**后再执行
- 如果涉及多个文件，明确说明每个文件的修改内容

#### 步骤 2: 阅读上下文

- **必须**使用工具阅读相关文件，不要凭空想象已有代码的结构
- 使用 `SearchCodebase` 或 `Read` 工具查看相关代码
- 检查 `src/utils/` 或 `src/core/` 是否有现成的工具函数

#### 步骤 3: 最小化修改

- **只修改**完成需求所必需的代码
- 如果只需要修改某个函数，**只输出该函数的修改**，或使用精确的查找替换（Search/Replace）格式
- **绝对不要**输出完整的文件内容，除非用户明确要求

#### 步骤 4: 自检

修改完成后，**必须**自己检查：
- [ ] 是否引入了 lint 错误（ruff check）
- [ ] 是否引入了类型错误（mypy）
- [ ] 是否破坏了现有测试（pytest）
- [ ] 是否符合项目的编码规范

---

## 5. 编码规范与铁律

### 5.1 绝对禁止

- ❌ **禁止直接实例化核心组件**：必须通过 `get_context()` 获取应用上下文
- ❌ **禁止在代码中硬编码任何密钥或敏感信息**：必须使用 `config` 模块
- ❌ **禁止使用 `# type: ignore`**：必须写出正确的类型注解
- ❌ **禁止擅自安装新的依赖**：如果需要，必须先向用户请示
- ❌ **禁止返回 `Dict[str, Any]`**：必须使用类型安全的数据类
- ❌ **禁止在 LazyFrame 中过早调用 `.collect()`**：仅最终输出时调用
- ❌ **禁止使用裸 `Exception`**：必须使用 `from src.core.exceptions import ...` 自定义异常
- ❌ **禁止引入复杂设计模式**：保持代码简单直白，一个简单的 if/else 如果能解决问题，就用 if/else

### 5.2 必须遵守

- ✅ **所有数据库查询必须使用 LazyFrame**：保持延迟求值，优化性能
- ✅ **错误处理必须使用项目统一的异常类**：`from src.core.exceptions import ...`
- ✅ **类名使用 PascalCase，函数/变量使用 snake_case，常量使用 UPPER_SNAKE_CASE**
- ✅ **核心模块类型注解覆盖率 ≥ 80%**
- ✅ **在编写新功能前，必须先搜索 `src/core/` 和 `src/utils/` 目录**，如果已有现成函数，必须复用，禁止重复造轮子
- ✅ **所有新增字段/工具，必须更新 Schema/TOOL_DESCRIPTIONS**

### 5.3 依赖注入规范 (v0.9.0新增)

#### ✅ 正确做法

```python
from src.core.context import get_context

def some_function():
    context = get_context()
    storage = context.storage      # 通过上下文获取
    analytics = context.analytics  # 通过上下文获取
    session_repo = context.session_repo  # 通过上下文获取
```

#### ❌ 错误做法

```python
from src.core.storage import StorageManager

def some_function():
    storage = StorageManager()  # 禁止直接实例化
```

### 5.4 SessionRepository 使用规范 (v0.9.0新增)

#### ✅ 正确做法

```python
from src.core.context import get_context
from src.core.session_repository import SessionSummary, SessionDetail

context = get_context()
session_repo = context.session_repo

# 使用类型安全的返回值
summary: SessionSummary = session_repo.get_session_summary(session_id)
detail: SessionDetail = session_repo.get_session_detail(session_id)
```

#### ❌ 错误做法

```python
# 禁止返回 Dict[str, Any]
result: Dict[str, Any] = session_repo.get_session_summary(session_id)
```

### 5.5 Polars 规范

#### ✅ 正确做法

```python
# 保持 LazyFrame，仅最终输出时调用 .collect()
lf = pl.scan_parquet("data.parquet")
result = lf.filter(pl.col("distance") > 10).collect()  # 仅在最终输出时 collect
```

#### ❌ 错误做法

```python
# 过早调用 .collect()，导致内存压力
df = pl.read_parquet("data.parquet")  # 立即加载到内存
result = df.filter(pl.col("distance") > 10)
```

---

## 6. 常用命令

**v0.9.0 CLI分层**：命令按领域分组，格式为 `nanobotrun <domain> <command>`。

### 依赖管理

```bash
uv venv                                          # 创建虚拟环境
uv sync --all-extras                             # 同步依赖
uv cache clean; if($?) { uv sync --reinstall }   # 清理重装 (Windows)
```

### 数据管理

```bash
uv run nanobotrun data import <path> [--force]   # 导入FIT文件
uv run nanobotrun data stats [--year YYYY]       # 查看统计
uv run nanobotrun data stats --start 2024-01-01 --end 2024-12-31  # 日期范围
```

### 数据分析

```bash
uv run nanobotrun analysis vdot      # VDOT趋势分析
uv run nanobotrun analysis load      # 训练负荷分析
uv run nanobotrun analysis hr-drift  # 心率漂移分析
```

### Agent交互

```bash
uv run nanobotrun agent chat         # 启动AI助手
```

### 报告生成

```bash
uv run nanobotrun report weekly      # 生成周报
uv run nanobotrun report monthly     # 生成月报
```

### 系统管理

```bash
uv run nanobotrun system config      # 查看配置
uv run nanobotrun system version     # 查看版本
```

### 测试

```bash
uv run pytest tests/unit/                        # 单元测试
uv run pytest -k "test_calculate_vdot"           # 按关键字
uv run pytest tests/unit/ --cov=src --cov-report=term-missing  # 覆盖率报告
```

### 代码质量

```bash
uv run ruff format src/ tests/           # 代码格式化
uv run ruff check src/ tests/            # 代码质量检查
uv run ruff check --fix src/ tests/      # 自动修复问题
uv run mypy src/ --ignore-missing-imports  # 类型检查
```

> **Windows PowerShell 注意**：多命令链用 `; if($?) { cmd }` 替代 `&&`

---

## 7. 测试策略

### 测试范围

- ✅ **必须编写单元测试**：核心业务逻辑（`src/core/`）
- ✅ **必须编写集成测试**：模块间交互（`tests/integration/`）
- ⚠️ **可选编写E2E测试**：端到端业务流程（`tests/e2e/`）

### 测试文件位置

- 单元测试：`tests/unit/` 目录下，与源码结构对应
- 集成测试：`tests/integration/` 目录下
- E2E测试：`tests/e2e/` 目录下

### Mock 策略

- ✅ **必须 Mock 外部 API 调用**：飞书通知、LLM 调用
- ❌ **禁止 Mock 内部业务逻辑**：保持测试真实性
- ✅ **使用 `unittest.mock.Mock`**：统一 Mock 工具

### 测试数据

- 测试样本：`tests/data/fixtures/*.fit`
- **禁止使用真实用户数据**：必须使用脱敏数据

---

## 8. 业务术语

### 核心概念

| 术语 | 定义 | 示例 |
|------|------|------|
| **Session** | 一次完整的跑步活动记录 | 2024-01-15 的晨跑记录 |
| **VDOT** | 跑力值，衡量跑者有氧能力的指标 | VDOT 45.2 表示中等水平 |
| **TSS** | 训练压力分数，衡量单次训练强度 | TSS 150 表示高强度训练 |
| **ATL** | 急性训练负荷，7天EWMA | ATL 50 表示近期训练负荷较高 |
| **CTL** | 慢性训练负荷，42天EWMA | CTL 65 表示体能基础扎实 |
| **TSB** | 训练压力平衡，CTL - ATL | TSB +10 表示体能充沛 |
| **心率漂移** | 有氧能力评估指标 | 相关性<-0.7 判定为漂移 |

### 数据结构

| 数据类 | 用途 | 位置 |
|--------|------|------|
| `SessionSummary` | Session 摘要数据 | `src/core/session_repository.py` |
| `SessionDetail` | Session 详细数据 | `src/core/session_repository.py` |
| `SessionVdot` | Session VDOT 数据 | `src/core/session_repository.py` |

---

## 9. 详细文档索引

| 文档 | 路径 | 内容 |
|------|------|------|
| 架构设计 | `docs/architecture/架构设计说明书.md` | 系统架构、模块设计、数据流 |
| API 参考 | `docs/api/api_reference.md` | 核心类和方法签名 |
| CLI 使用 | `docs/guides/cli_usage.md` | 命令详解、参数说明 |
| Agent 配置 | `docs/guides/agent_config_guide.md` | 配置文件、路径说明 |
| 开发指南 | `docs/guides/development_guide.md` | Polars 规范、异常处理、类型注解 |
| Agent 工具扩展 | `docs/guides/agent_tools_guide.md` | 新增工具步骤、TOOL_DESCRIPTIONS |
| 测试指南 | `docs/guides/testing_guide.md` | Mock 策略、测试数据、隐私红线 |

---

## 10. 路径速查

| 类型 | 路径 |
|------|------|
| 框架配置 | `~/.nanobot/config.json` |
| 业务配置 | `~/.nanobot-runner/config.json` |
| 跑步数据 | `~/.nanobot-runner/data/activities_*.parquet` |
| 用户画像 | `~/.nanobot-runner/data/profile.json` |
| Agent 记忆 | `~/.nanobot-runner/memory/MEMORY.md` |
| 测试样本 | `tests/data/fixtures/*.fit` |

---

## 11. 提交前 Checklist

- [ ] `uv run ruff format --check src/ tests/` 零警告
- [ ] `uv run ruff check src/ tests/` 零警告
- [ ] `uv run mypy src/` 无新增错误
- [ ] `uv run pytest tests/unit/` 通过率 100%
- [ ] 新增字段/工具 → 更新 Schema/TOOL_DESCRIPTIONS
- [ ] 修改核心逻辑 → 补充单元测试

---

## 12. 常见问题与陷阱

### 陷阱 1: 过度工程化

**问题**: AI 喜欢引入设计模式，导致代码晦涩难懂。

**解决方案**: 保持代码简单直白。除非明确要求，否则不要引入工厂模式、策略模式等复杂设计。一个简单的 if/else 如果能解决问题，就用 if/else。

### 陷阱 2: 忽略现有工具

**问题**: AI 经常重复造轮子，忽略项目中已有的工具函数。

**解决方案**: 在编写新功能前，**必须**先搜索 `src/core/` 和 `src/utils/` 目录，如果已有现成函数，必须复用。

### 陷阱 3: 全文件重写

**问题**: AI 经常重写整个文件，导致 diff 爆炸或丢失未提交的代码。

**解决方案**: 如果只需要修改某个函数，**只输出该函数的修改**，或使用精确的查找替换（Search/Replace）格式，**绝对不要**输出完整的文件内容。

### 陷阱 4: 类型注解缺失

**问题**: AI 经常忽略类型注解，导致 mypy 报错。

**解决方案**: 所有函数参数和返回值**必须**添加类型注解，核心模块覆盖率 ≥ 80%。

---

*文档版本: v5.0.0 | 更新日期: 2026-04-11*
