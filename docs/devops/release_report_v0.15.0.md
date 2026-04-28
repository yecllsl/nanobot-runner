# v0.15.0 发布报告

## 基本信息

| 项目 | 内容 |
|------|------|
| 版本号 | 0.15.0 |
| 发布日期 | 2026-04-28 |
| 发布模式 | 单人自动化发布 |
| 发布分支 | main |
| 提交哈希 | c20bf2d |
| GitHub Release | [v0.15.0](https://github.com/yecllsl/nanobot-runner/releases/tag/0.15.0) |

---

## 发布内容

### 新增功能

#### 1. AI 决策透明化模块
- **透明化引擎 (TransparencyEngine)**: AI 决策过程透明化
  - 决策过程追踪：记录 Agent 每一步决策的输入、推理过程和输出
  - 工具调用追踪：详细记录每个工具调用的参数、执行结果和耗时
  - 决策链路可视化：支持生成决策过程的可视化报告

- **可观测性管理器 (ObservabilityManager)**: 系统可观测性管理
  - AI 状态仪表盘：实时监控 AI 助手状态、响应时间、错误率
  - 训练洞察报告：自动生成训练数据分析洞察报告
  - 性能指标采集：采集并存储关键性能指标

- **追踪日志器 (TraceLogger)**: 结构化追踪日志
  - 支持决策树结构的日志记录
  - 支持多层级嵌套决策追踪
  - 日志持久化到本地文件

- **透明化展示 (TransparencyDisplay)**: 决策过程可视化展示
  - 支持终端 Rich 表格展示决策详情
  - 支持生成 Markdown 格式洞察报告
  - 支持决策链路时间线展示

#### 2. 报告导出功能增强
- **周报/月报告导出**: 为 `report generate` 命令添加 `--output` 选项
  - 支持将周报/月报保存为 Markdown 文件
  - 支持自定义输出文件路径
  - 保持报告格式与终端输出一致

#### 3. 核心解析器增强
- **Mock 文件检测**: 新增 `_is_mock_file` 方法
  - 自动检测 Mock 文本文件，避免误解析
  - 提升 FIT 文件解析的健壮性

#### 4. CLI 命令扩展
- `nanobotrun transparency trace`: 查看 AI 决策追踪日志
- `nanobotrun transparency status`: 查看 AI 状态仪表盘
- `nanobotrun transparency insight`: 生成训练洞察报告
- `nanobotrun report generate --type weekly --output report.md`: 导出周报到文件
- `nanobotrun report generate --type monthly --output report.md`: 导出月报到文件

### CI/CD 修复
- 修复 GitHub Actions 中清华镜像源 403 错误
- 修复 CI 环境 ANSI 转义码导致测试失败问题
- 修复 Python 3.12 测试依赖安装失败问题

---

## 发布流程执行记录

### 1. 发布前验证

| 检查项 | 状态 | 说明 |
|--------|------|------|
| CI 流水线 | ✅ 通过 | Run ID: 25042395976 |
| 代码格式化 | ✅ 通过 | ruff format |
| 代码质量 | ✅ 通过 | ruff check |
| 类型检查 | ✅ 通过 | mypy |
| 安全扫描 | ✅ 通过 | bandit |
| 单元测试 | ✅ 通过 | pytest (30.29s) |
| 敏感信息检测 | ✅ 通过 | 无硬编码密钥 |

### 2. 版本更新

| 文件 | 变更内容 |
|------|----------|
| `pyproject.toml` | version: 0.13.0 → 0.15.0 |
| `CHANGELOG.md` | 新增 0.15.0 版本更新记录 |

### 3. Git 操作

| 操作 | 状态 | 详情 |
|------|------|------|
| 提交代码 | ✅ 完成 | c20bf2d |
| 创建 Tag | ✅ 完成 | 0.15.0 (annotated) |
| 推送代码 | ✅ 完成 | main → origin/main |
| 推送 Tag | ✅ 完成 | 0.15.0, 0.14.0 |
| 创建 Release | ✅ 完成 | [GitHub Release](https://github.com/yecllsl/nanobot-runner/releases/tag/0.15.0) |

### 4. 测试覆盖

| 模块 | 覆盖率 | 状态 |
|------|--------|------|
| 透明化引擎 | 92% | ✅ |
| 可观测性管理器 | 80% | ✅ |
| 整体测试通过率 | 100% | ✅ |

| 测试类型 | 数量 | 状态 |
|----------|------|------|
| 单元测试 | 61个（透明化模块） | ✅ |
| 集成测试 | 7个（透明化链路） | ✅ |
| E2E 测试 | 5个（端到端用户旅程） | ✅ |

---

## 版本对比

- 上一版本: [0.14.0](https://github.com/yecllsl/nanobot-runner/releases/tag/0.14.0)
- 当前版本: [0.15.0](https://github.com/yecllsl/nanobot-runner/releases/tag/0.15.0)
- 变更提交数: 6 (自 0.14.0 以来)

---

## 已知问题

无

---

## 发布结论

✅ **v0.15.0 版本发布成功**

- 所有预提交检查通过
- CI 流水线执行成功
- 测试覆盖率达标
- GitHub Release 已创建
- 版本文档已更新

---

## 发布人

- 发布执行: DevOps 智能体
- 发布时间: 2026-04-28 16:48
