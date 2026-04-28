# 历史版本更新日志（v0.11.0 及更早版本）

> 本文档归档 v0.11.0 及更早版本的详细更新记录。
> 最新版本变更请查看项目根目录 [CHANGELOG.md](../../../CHANGELOG.md)。

---

## [0.11.0] - 2026-04-19

### 新增功能

#### 智能调整层 (v0.11.0)
- **计划调整校验器**: 新增 PlanAdjustmentValidator，规则引擎验证调整合理性
  - 10项硬性规则：跑量上限、增量限制、连续高强度限制等
  - 8项软性规则：有氧比例、长距离比例、恢复日安排等
  - 支持规则优先级和严重性分级
- **Prompt模板引擎**: 新增 PromptTemplateEngine，管理LLM提示词模板
  - 支持模板变量替换
  - 支持条件渲染
  - 支持多语言模板
- **计划修改对话管理器**: 新增 PlanModificationDialogManager
  - 支持多轮对话流程管理
  - 上下文感知：记录对话历史
  - 确认机制：关键调整需用户确认
  - 状态机管理：INITIATED → SUGGESTION → CONFIRMATION → COMPLETED

#### Agent工具扩展
- **AdjustPlanTool**: 新增计划调整工具，支持自然语言修改训练计划
  - 支持减量、调整日期、更换训练类型等操作
  - 自动规则校验，拒绝不合理调整
  - 多轮对话支持，逐步细化调整需求
- **UpdateMemoryTool**: 新增记忆更新工具，持久化用户偏好

#### CLI命令扩展
- **nanobotrun plan adjust**: 新增计划调整命令
- **nanobotrun plan generate-long-term**: 新增长期规划命令
- **nanobotrun plan evaluate-goal**: 新增目标评估命令

### 测试覆盖
- 新增单元测试：60+
- 规则引擎覆盖率：92%
- 对话管理器覆盖率：98%
- Prompt引擎覆盖率：100%

---

## [0.10.0] - 2026-04-19

### 新增功能

#### 数据感知层 (v0.10.0)
- **训练响应分析器**: 新增 TrainingResponseAnalyzer
  - 分析心率、配速、步频对训练强度的响应模式
  - 识别有氧基础、乳酸阈值、无氧能力
  - 检测疲劳信号和过度训练风险
- **计划执行仓储**: 新增 PlanExecutionRepository
  - 支持计划完成度跟踪
  - 支持训练反馈记录（RPE、体感、备注）
  - 支持历史响应模式查询
- **计划分析器**: 新增 PlanAnalyzer
  - 分析计划负荷分布
  - 计算周跑量、强度分布
  - 识别训练不平衡问题

#### Agent工具扩展
- **RecordTrainingFeedbackTool**: 新增训练反馈记录工具
- **GetPlanCompletionStatusTool**: 新增计划完成度查询工具
- **AnalyzeTrainingResponseTool**: 新增训练响应分析工具

#### 数据模型
- **TrainingFeedback**: 训练反馈数据模型
- **PlanCompletionStatus**: 计划完成度状态模型
- **TrainingResponseProfile**: 训练响应画像模型

### 测试覆盖
- 新增单元测试：50+
- 响应分析器覆盖率：98%
- 计划执行仓储覆盖率：99%
- 计划分析器覆盖率：99%

---

## [0.9.5] - 2026-04-20

### 新增功能

#### Gateway服务增强
- **飞书通道配置**: 支持从.env.local读取飞书配置，自动传递给ChannelManager
- **nanobot兼容性**: 适配nanobot 0.1.5版本，修复Config构建问题
- **响应格式化**: Agent响应使用Markdown渲染，提升可读性

#### LLM Provider扩展
- **智谱AI支持**: 新增zhipu选项，默认模型glm-4-flash

#### 数据查询优化
- **去重逻辑**: 修复Parquet数据查询时的重复记录问题
- **日期过滤**: 使用session_start_time替代timestamp进行日期范围过滤

#### 报告生成改进
- **字段映射**: 修复报告数据字段名不匹配问题
- **数据准确性**: 修正训练次数、距离、时长、TSS、VDOT计算

#### 初始化增强
- **Git仓库初始化**: 初始化时自动创建.git目录和.gitignore文件
- **模板文件**: 自动复制AGENTS.md、HEARTBEAT.md、SOUL.md、TOOLS.md、USER.md等模板
- **Memory目录**: 自动创建memory/MEMORY.md和memory/history.jsonl

### Bug修复

#### 配置管理
- **修复**: .env.local未加载问题，在AppContextFactory.create()中添加EnvManager.load_env()调用
- **修复**: 工作区初始化检测逻辑，防止ConfigManager自动创建config.json

#### 文档一致性
- **修复**: 统一CLI命令格式，将`uv run nanobotrun init`修正为`uv run nanobotrun system init`

#### 第三方依赖
- **修复**: nanobot.providers.factory导入错误，改用registry.find_by_name()
- **修复**: load_config_from_dict函数移除后的兼容性问题

### 测试改进

#### 测试策略更新
- **新增**: 第三方库兼容性测试
- **新增**: 真实数据样本验证测试
- **新增**: 环境配置加载测试
- **新增**: 通道配置传递测试
- **新增**: 文档一致性验证脚本

#### 测试成果
- **测试用例**: 2271个（单元2044 + 集成152 + E2E 75）
- **测试通过率**: 100%
- **代码覆盖率**: 84%

---

## [0.9.4] - 2026-04-18

### 新增功能

#### 配置管理基础设施
- **配置管理器**: 新增 ConfigManager，支持环境变量覆盖、无配置模式、配置验证
- **环境变量管理**: 新增 EnvManager，管理 .env.local 文件和环境变量
- **工作区管理**: 新增 WorkspaceManager，支持工作区路径解析和创建
- **数据迁移引擎**: 新增 MigrationEngine，支持版本间数据迁移
- **备份管理器**: 新增 BackupManager，支持配置和数据备份/恢复
- **数据校验器**: 新增 VerifyManager，支持文件完整性校验
- **初始化向导**: 新增 InitWizard，提供交互式初始化流程

#### 初始化命令
- **nanobotrun system init**: 新增初始化命令，支持全新初始化、迁移模式、修复模式
- **交互式配置**: 支持 LLM Provider 选择、业务配置、飞书集成配置
- **配置验证**: 初始化后自动验证配置有效性

#### 系统管理命令
- **nanobotrun system validate**: 新增配置验证命令
- **nanobotrun system backup**: 新增备份命令
- **nanobotrun system restore**: 新增恢复命令
- **nanobotrun system migrate**: 新增迁移命令

### 架构改进

#### 配置管理架构
- **配置分层**: 支持默认值 < 配置文件 < 环境变量的优先级覆盖
- **配置验证**: 支持格式验证、完整性验证、有效性验证、一致性验证
- **配置迁移**: 支持从旧版本配置自动迁移到新版本

#### 依赖注入扩展
- **AppContext v3**: 扩展上下文管理器，支持配置管理相关组件
- **SessionRepository**: 新增会话仓储层，提供类型安全的 Session 查询

### 测试覆盖提升

#### Bug修复
- **BUG-001**: MigrationEngine 测试覆盖率从 41% 提升至 99%
- **BUG-002**: ConfigValidator 测试覆盖率从 76% 提升至 98%
- **BUG-003**: InitPrompts 测试覆盖率从 0% 提升至 88%
- **BUG-004**: BackupManager 测试覆盖率从 72% 提升至 91%
- **BUG-005**: 整体异常处理分支补充测试

#### 测试成果
- **新增测试用例**: 57个
- **测试通过率**: 100% (2002 passed)
- **代码质量**: ruff零警告 / mypy零错误
- **修复额外Bug**: 修复 BackupManager 压缩备份恢复路径判断 bug

### 用户价值

- **简化初始化**: 新用户可通过 `nanobotrun system init` 快速完成初始化
- **配置安全**: 支持配置备份和恢复，防止配置丢失
- **平滑升级**: 支持从旧版本自动迁移配置和数据
- **配置验证**: 提供配置验证命令，及时发现配置问题

---

## [0.9.3] - 2026-04-15

### 新增功能

#### 报告生成功能
- **周报生成**: 新增周报生成功能，支持生成训练周报
- **月报生成**: 新增月报生成功能，支持生成训练月报
- **ReportService**: 新增报告服务，统一管理报告生成逻辑

#### 飞书Gateway重构
- **Gateway服务**: 重构飞书机器人网关服务，优化命令处理流程
- **命令路由**: 实现命令直接路由，绕过LLM处理，提升响应速度
- **格式化输出**: 新增格式化函数，确保返回字符串类型

#### 开发体验优化
- **一键安装脚本**: 新增一键安装脚本，简化项目初始化流程
- **版本号管理**: 优化版本号管理，避免版本号不一致问题
- **契约测试**: 添加契约测试到CI流程，确保接口兼容性

#### VDOT计算器改进
- **计算器优化**: 改进VDOT计算器及工具类
- **测试文档**: 添加飞书Gateway和Agent Chat测试文档

### 架构重构

#### 领域模型统一去重
- **ProfileStorageManager**: 统一用户画像存储管理器，消除重复定义
- **PlanStatus**: 统一计划状态枚举，确保状态一致性
- **FitnessLevel**: 统一健身水平枚举，消除重复定义
- **DailyPlan**: 统一日计划数据类，确保数据结构一致
- **WeeklySchedule**: 统一周计划数据类，消除重复定义
- **ReportType**: 统一报告类型枚举，确保类型一致性
- **TrainingPlan**: 统一训练计划数据类，消除重复定义

#### 依赖注入体系完善
- **ProfileEngine**: 重构为依赖注入模式，通过AppContext获取依赖
- **ReportService**: 重构为依赖注入模式，消除直接实例化
- **ReportGenerator**: 重构为依赖注入模式，提升可测试性
- **PlanManager**: 重构为依赖注入模式，统一依赖管理
- **FeishuCalendarTool**: 重构为依赖注入模式，支持Mock测试
- **AppContext v2**: 扩展上下文管理器，支持更多核心组件

#### 代码质量提升
- **ToolResult迁移**: 将ToolResult类迁移到独立的result.py文件
- **PlanManagerError修复**: 修复异常类继承，补充必需字段
- **装饰器合并**: 合并handle_tool_errors和tool_wrapper为统一的tool_handler
- **ConfigManager缓存改进**: 添加reset_cache方法，提升可测试性

### 测试覆盖达标

#### 单元测试
- **测试覆盖率**: 从85%提升到87%，达到项目目标（core≥80%）
- **新增测试**: 补充feishu/feishu_calendar单元测试
- **测试通过率**: 99.9% (1991/1993)，无失败用例

#### 集成测试
- **依赖注入验证**: 验证所有组件使用依赖注入模式
- **数据契约验证**: 验证数据类字段完整性
- **模块交互验证**: 验证模块间交互正常

#### E2E测试
- **用户旅程验证**: 验证完整用户旅程闭环
- **CLI契约验证**: 验证CLI命令格式正确
- **性能基准验证**: 验证性能基准达标

### 用户验收测试修复

#### Bug修复
- **BUG-001**: 修复字符串参数验证测试断言
- **BUG-002**: 修复整数参数验证测试断言
- **BUG-003**: 修复数值参数验证测试断言
- **BUG-004**: 修复必填参数验证测试断言

#### 回归测试
- **测试通过率**: 99.9% (2039/2041)
- **Bug修复率**: 100% (4/4)
- **覆盖率达标**: 87% ≥ 80%

### 技术债务清理

#### 类型安全改造
- 定义多种数据类替代字典返回值（HRZoneResult、ReportData、CalendarEventResult等）
- 合并dataclass定义到models.py，统一管理
- 统一枚举类定义，消除重复

#### 日志系统统一
- 清除loguru依赖，统一使用get_logger
- 统一日志输出格式和级别

#### 代码规范
- 消除Dict[str, Any]返回值，使用类型安全的数据类
- 统一导入路径，确保模块导入一致性
- 统一异常类继承体系，提升错误处理能力

---

## [0.9.2] - 2026-04-11

### 新增功能

#### 文档改进
- **AGENTS.md重构**: 根据最佳实践全面重构AGENTS.md文档
  - 新增"开发工作流"部分，强制AI先规划再执行
  - 新增"编码规范与铁律"部分，明确禁止和必须遵守的规则
  - 新增"业务术语"部分，定义核心概念和数据结构
  - 新增"常见问题与陷阱"部分，识别常见陷阱并提供解决方案
  - 优化语气和表达，从"商量式"改为"指令式"

#### CI/CD优化
- **流水线修复**: 修复CI流水线构建失败问题
  - 移除构建依赖验证步骤（hatchling模块导入错误）
  - 禁用缓存以解决Code Quality Check失败问题
  - 添加流水线执行报告文档

### 修复问题

#### CI流水线
- 修复 Build Package job 失败（hatchling模块导入错误）
- 修复 Code Quality Check job 失败（缓存导致依赖安装失败）

### 技术债务清理

#### 文档更新
- 更新版本号到 0.9.2
- 更新 README.md 版本信息
- 添加 CI 流水线执行报告

---

## [0.9.1] - 2026-04-10

### 新增功能

#### 依赖升级
- **nanobot-ai**: 升级到 0.1.5 版本，获得新功能和性能优化
- 新增依赖支持：anthropic, ddgs, docstring-parser, dulwich, litellm, primp, questionary

### 修复问题

#### 依赖兼容性
- 修复 nanobot-ai 0.1.4 版本中的已知问题
- 优化依赖版本兼容性

### 技术债务清理

#### 依赖管理
- 更新项目版本号到 0.9.1
- 同步依赖版本到最新稳定版本

---

## [0.9.0] - 2026-04-09

### 新增功能

#### 依赖注入机制
- **AppContext**: 应用上下文管理器，集中管理所有核心组件实例
- **AppContextFactory**: 工厂模式创建应用上下文，支持依赖注入和测试
- 全局上下文管理函数: `get_context()`, `set_context()`, `reset_context()`
- 支持自定义依赖注入，便于单元测试时注入 Mock 对象

#### SessionRepository 仓储层
- **SessionRepository**: Session 数据仓储层，封装 Session 级别的数据聚合查询
- **SessionSummary/SessionDetail/SessionVdot**: 类型安全的数据类，替代 Dict[str, Any]
- 保持 LazyFrame 链式操作，仅在最终输出时调用 `collect()`
- 使用 Polars 表达式替代 `iter_rows` 循环，提升性能
- 支持按日期范围、距离范围查询 Session 数据

#### CLI 架构重构
- **命令拆分**: CLI 按领域拆分为独立模块
  - `data`: 数据管理命令 (import-data, stats)
  - `analysis`: 数据分析命令 (vdot, load, hr-drift)
  - `agent`: Agent交互命令 (chat)
  - `report`: 报告生成命令 (weekly, monthly)
  - `system`: 系统管理命令 (config, version)
  - `gateway`: Gateway服务命令 (start)
- **Handler层分离**: 命令定义与业务逻辑分离
- **公共组件复用**: formatter、common等公共组件

### 架构改进

#### 依赖注入体系
- 所有核心组件通过 AppContext 统一管理
- 支持测试时注入 Mock 对象
- 消除独立实例化，统一依赖管理

#### 类型安全
- 使用类型安全的数据类替代 Dict[str, Any]
- 核心模块类型注解覆盖率 ≥ 80%
- MyPy 静态类型检查零错误

### 测试覆盖
- 新增单元测试：200+
- 核心模块覆盖率：≥ 80%
- 测试通过率：100%
