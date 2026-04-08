# Nanobot Runner 深度设计分析报告

## 一、 系统架构概览

项目采用 **分层架构 + 插件化工具链** 设计，整体分为三层：
- **交互层**：Typer CLI (`cli.py`)、AI Agent (`agents/tools.py`)、飞书网关 (`notify/`)
- **业务层**：核心引擎 (`core/`)，包含解析、存储、分析、画像、报告、训练计划等
- **数据层**：FIT 原始文件 → Parquet 列式存储（按年分片） → JSON 配置/索引

**架构优势**：职责边界清晰，数据流单向，CLI 与 Agent 共享同一套核心逻辑，避免了重复实现。
**架构隐患**：业务层呈现“胖核心、薄外壳”特征，核心模块过度膨胀，缺乏明确的领域边界划分。

---

## 二、 模块划分与职责边界

| 模块 | 文件数 | 核心职责 | 健康度 |
|------|--------|----------|--------|
| `src/core/` | 18 | 数据解析、存储、索引、分析、画像、报告、计划 | ⚠️ 严重膨胀 |
| `src/agents/` | 1 | AI 工具桥接、OpenAI Schema 适配 | ⚠️ 职责混杂 |
| `src/notify/` | 2 | 飞书 IM 交互、日历同步 | ⚠️ 代码重复 |
| `src/cli.py` | 1 | 命令路由、进度展示、异步网关 | 🔴 上帝函数 |
| `src/cli_formatter.py` | 1 | Rich 格式化输出 | ✅ 良好 |

**核心问题**：
- `core/analytics.py` (1862行) 与 `core/profile.py` (1681行) 违反单一职责原则，承担了 VDOT 计算、TSS/ATL/CTL、心率漂移、训练负荷、日报生成、周计划、异常过滤、画像构建等 10+ 个独立领域逻辑。
- `agents/tools.py` (857行) 将工具定义、业务逻辑、工厂函数、文档描述全部塞入单文件。
- `cli.py` 中 `gateway()` 函数达 204 行，内嵌多个异步回调与依赖初始化，应独立为 `gateway_service.py`。

---

## 三、 核心数据流向分析

```
FIT文件 → FitParser(猴子补丁fitparse) → IndexManager(SHA256去重) 
        → StorageManager(Parquet按年分片) → LazyFrame查询
        → AnalyticsEngine/ProfileEngine → .collect() → CLI/Agent输出
```

**流向评估**：
- ✅ **Polars LazyFrame 管道**：查询阶段保持惰性计算，符合数据工程最佳实践。
- ⚠️ **写入路径低效**：`storage.py:save_to_parquet()` 每次导入都读取整个 Parquet 文件 → 拼接 → 去重 → 重写，时间复杂度 O(N)，数据量增长后将成瓶颈。
- ⚠️ **Schema 对齐过度复杂**：`_concat_with_schema_alignment()` 在循环中反复调用 `with_columns`，产生大量中间 DataFrame 副本。应改用批量表达式构建。
- ⚠️ **过早 collect**：`profile.py:filter_anomaly_data` 为打印日志高度调用两次 `.collect()`，破坏惰性求值优势。

---

## 四、 技术选型评估

| 技术 | 评估 | 风险等级 |
|------|------|----------|
| **Polars + Parquet** | 列式存储+惰性计算，适合分析型负载。按年分片合理。 | 🟢 低 |
| **Typer + Rich** | 现代 Python CLI 栈，开发体验好，类型提示友好。 | 🟢 低 |
| **fitparse** | FIT 解析事实标准，但需猴子补丁处理非标准字段。 | 🟡 中 |
| **nanobot-ai** | 自定义 AI 框架，版本约束 `>=0.1.4` 无上限。 | 🔴 高 |
| **JSON 配置/索引** | 简单直观，但无并发控制、无事务、无结构校验。 | 🟡 中 |
| **requests (异步环境)** | `feishu_calendar.py` 在 `async def` 中同步阻塞调用。 | 🟡 中 |

---

## 五、 设计模式应用分析

| 模式 | 应用位置 | 评价 |
|------|----------|------|
| **Facade** | `ImportService`, `RunnerTools`, `ReportGenerator` | ✅ 封装复杂子系统，接口清晰 |
| **Command/Strategy** | `BaseTool` 子类、飞书命令处理器 | ✅ 易于扩展新工具 |
| **Template Method** | 报告模板引擎 (`TemplateEngine`) | ✅ 配置驱动，解耦数据与渲染 |
| **Repository** | `StorageManager` | ✅ 抽象数据访问层 |
| **Module Singleton** | `config.py`, `logger.py` | ⚠️ 隐式全局状态，测试困难 |
| **Adapter** | `BaseTool.to_schema()` 转 OpenAI 格式 | ✅ 框架解耦 |

**模式滥用/缺失**：
- 缺乏 **Dependency Injection**：几乎所有命令都直接 `StorageManager()` 实例化，难以 Mock 和替换。
- 缺乏 **Observer/Event Bus**：数据导入、报告生成、飞书推送之间通过硬编码调用耦合，未使用事件驱动解耦。

---

## 六、 代码结构合理性评估

**合理之处**：
- 目录结构符合 Python 包规范，核心/代理/通知分离清晰。
- 异常体系完整 (`exceptions.py`)，包含错误码、恢复建议、`to_dict()`。
- 类型注解覆盖率较高，符合 AGENTS.md 要求。

**结构缺陷**：
1. **上帝类 (God Classes)**：`AnalyticsEngine` 和 `ProfileEngine` 承担过多职责，内聚性差。
2. **重复代码**：
   - 会话聚合逻辑 `group_by("session_start_time").agg([...]).sort(...).collect()` 在 `tools.py` 中出现 4 次。
   - 飞书 Token 管理在 `feishu.py` 和 `feishu_calendar.py` 中几乎复制粘贴。
   - `get_running_summary` 与 `get_running_stats` 逻辑高度重叠。
3. **延迟导入泛滥**：`cli.py` 和 `tools.py` 大量使用函数内 `import` 掩盖循环依赖，说明模块间存在隐式耦合环。
4. **错误处理不一致**：部分方法返回 `{"error": "..."}` 字典，部分抛出自定义异常，部分返回友好消息。调用方需处理三种契约。

---

## 七、 扩展性与可维护性

| 维度 | 现状 | 扩展难度 |
|------|------|----------|
| **新增指标** | 需修改 1800+ 行的 `AnalyticsEngine` | 🔴 高 |
| **新增 Agent 工具** | 需在 857 行文件中添加类+注册+更新 `TOOL_DESCRIPTIONS` | 🟡 中 |
| **多数据源** | 强依赖 FIT → Parquet 管道，无抽象数据源接口 | 🔴 高 |
| **多用户/云端** | 架构设计为单用户本地，路径硬编码 `~/.nanobot-runner` | 🔴 高 |
| **测试** | mypy 配置极度宽松，类型检查形同虚设 | 🟡 中 |

---

## 八、 性能瓶颈分析

1. **Parquet 写入放大** (`storage.py:save_to_parquet`)：全量读取+重写，导入 100 个文件后可能需处理 MB 级数据，I/O 开销呈线性增长。
2. **配置频繁磁盘 I/O** (`config.py:get()`)：每次调用都 `load_config()` 读盘解析 JSON，无内存缓存。
3. **索引无并发控制** (`indexer.py`)：多进程/多线程导入时 `index.json` 可能损坏。
4. **Polars 循环列操作** (`schema.py:normalize_dataframe`)：逐列调用 `with_columns` 而非批量构建表达式，产生 N 个中间 LazyFrame。
5. **异步阻塞** (`feishu_calendar.py`)：`async def` 方法内使用同步 `requests`，阻塞事件循环，降低网关吞吐量。

---

## 九、 安全风险评估

| 风险点 | 位置 | 严重性 | 说明 |
|--------|------|--------|------|
| 明文存储凭证 | `~/.nanobot-runner/config.json` | 🟡 中 | 飞书 App ID/Secret 未加密 |
| 路径遍历风险 | `cli.py:import_data` | 🟢 低 | 未校验用户传入的路径是否超出预期目录 |
| 全局猴子补丁 | `parser.py:16-86` | 🟡 中 | 修改 `fitparse` 内部行为，影响同进程所有使用者 |
| 裸异常捕获 | `tools.py:113`, `decorators.py` | 🟢 低 | 掩盖底层 bug，违反项目规范 |
| 依赖供应链 | `pyproject.toml` | 🟡 中 | `nanobot-ai>=0.1.4` 无上限，破坏性更新将直接瘫痪应用 |

---

## 十、 维护成本分析

- **认知负荷高**：新开发者需阅读 3000+ 行核心类才能理解指标计算逻辑。
- **测试成本高**：模块级单例、隐式全局状态、硬编码路径导致单元测试需大量 Mock。
- **版本管理混乱**：`pyproject.toml` 声明 `0.8.0`，`src/__init__.py` 为 `0.4.0`，发布流程缺乏自动化校验。
- **文档与代码脱节**：`TOOL_DESCRIPTIONS` 手动维护，易与工具实际参数漂移。
- **CI/CD 缺失**：mypy 配置关闭了几乎所有检查，类型安全承诺未落地。

---

## 十一、 具体改进建议（按优先级）

### 🔴 P0：立即修复
1. **拆分上帝类**：将 `AnalyticsEngine` 拆分为 `VDOTCalculator`, `TrainingLoadAnalyzer`, `HRZoneAnalyzer`, `ReportGenerator` 等独立服务。
2. **修复 Parquet 写入路径**：改用 `pyarrow.parquet.ParquetWriter` 追加模式，或引入 Delta Lake 实现 ACID 追加。
3. **统一错误契约**：核心层全部使用自定义异常，工具层通过 `@handle_tool_errors` 统一转为字典。
4. **修复版本不一致**：CI 中增加 `pyproject.toml` 与 `__version__` 一致性检查。

### 🟡 P1：短期优化
5. **提取重复逻辑**：会话聚合提取为 `_aggregate_sessions(lf, filters)`，飞书 Token 管理提取为共享 `FeishuAuth`。
6. **引入依赖注入**：CLI 命令通过构造函数或上下文接收依赖，替代全局实例化。
7. **收紧 mypy 配置**：逐步开启 `disallow_untyped_defs`, `check_untyped_defs`，提升类型安全。
8. **替换同步请求**：`feishu_calendar.py` 改用 `httpx` 或 `aiohttp` 实现真正异步。

### 🟢 P2：长期演进
9. **抽象数据源接口**：定义 `DataSource` 协议，为未来支持 TCX/GPX/Strava API 做准备。
10. **事件驱动架构**：引入轻量级事件总线，解耦导入、分析、报告、推送流程。
11. **配置加密**：使用 `cryptography` 或系统 Keychain 存储敏感凭证。
12. **工具自动注册**：使用 `__init_subclass__` 或装饰器自动发现工具，消除手动注册与文档漂移。

---

## 十二、 关键设计决策的长期影响

| 决策 | 短期收益 | 长期影响 | 建议 |
|------|----------|----------|------|
| **Parquet 替代 SQLite** | 分析查询极快，列式压缩率高 | 频繁小写入性能差，不支持事务/并发 | 数据量 > 500 次跑步后考虑 Delta Lake |
| **单用户本地架构** | 零运维，隐私安全，开发快 | 无法支持多设备同步、云端分析、商业化 | 保持定位，但预留 `DataSource` 抽象 |
| **猴子补丁 fitparse** | 快速兼容非标 FIT 文件 | 库升级易断裂，全局副作用不可控 | 向 `fitparse` 上游提 PR 或封装独立解析器 |
| **紧耦合 nanobot-ai** | 快速实现 Agent 能力 | 框架锁定，升级/替换成本极高 | 定义 `AgentFramework` 接口层隔离 |
| **按年分片 Parquet** | 查询过滤快，文件管理简单 | 跨年查询需合并多个 LazyFrame | 引入分区元数据缓存，优化路由 |

---

**总结**：Nanobot Runner 在数据工程选型（Polars/Parquet）和 CLI 交互设计上表现优秀，核心数据管道清晰。但业务逻辑层严重膨胀，缺乏领域划分与依赖管理，已成为扩展与维护的主要瓶颈。建议优先执行 **P0 级重构**（拆分上帝类、优化存储写入、统一错误处理），并逐步引入依赖注入与事件驱动架构，以支撑未来 1-2 年的功能迭代。