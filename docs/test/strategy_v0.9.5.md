# v0.9.5 版本测试策略

> **文档版本**: v1.0  
> **适用版本**: v0.9.5  
> **编写日期**: 2026-04-20  
> **编写依据**: UAT测试反馈问题总结与改进

---

## 1. 测试范围

### 1.1 核心功能模块

| 模块 | 测试重点 | 测试类型 |
|------|---------|---------|
| **数据导入** | FIT文件解析、SHA256去重、批量导入 | 单元测试+集成测试 |
| **数据查询** | Parquet查询、日期范围过滤、统计计算 | 单元测试+集成测试 |
| **数据分析** | VDOT计算、TSS/ATL/CTL/TSB、心率漂移 | 单元测试+集成测试 |
| **配置管理** | .env.local加载、配置验证、初始化向导 | 集成测试+E2E测试 |
| **报告生成** | 周报/月报数据准确性、字段映射 | 集成测试+E2E测试 |
| **Gateway服务** | 飞书通道配置、nanobot兼容性、通道启动 | 集成测试+E2E测试 |
| **Agent交互** | LLM Provider配置、工具注册、响应格式化 | 集成测试 |

### 1.2 新增测试范围（基于UAT反馈）

| 测试类型 | 测试内容 | 测试方法 |
|---------|---------|---------|
| **第三方库兼容性** | nanobot版本变更适配、API兼容性 | 集成测试 |
| **真实数据验证** | 使用真实Parquet数据样本验证查询 | 集成测试 |
| **环境配置加载** | .env.local文件加载流程验证 | 集成测试 |
| **通道配置传递** | 飞书配置从.env.local到ChannelManager的完整流程 | 集成测试 |
| **文档一致性** | CLI命令与文档一致性验证 | 自动化脚本 |

---

## 2. 测试类型

### 2.1 单元测试（Unit Tests）

**目标**: 验证单个函数/类的正确性

**覆盖率要求**:
| 模块 | 覆盖率要求 | 当前状态 |
|------|-----------|---------|
| `src/core/` | ≥80% | 待评估 |
| `src/agents/` | ≥70% | 待评估 |
| `src/cli/` | ≥60% | 待评估 |

**测试重点**:
- 核心业务逻辑（VDOT计算、TSS计算、心率漂移）
- 数据处理（Parquet读写、SHA256去重）
- 配置解析（config.json、.env.local）
- 异常处理（错误场景、边界条件）

### 2.2 集成测试（Integration Tests）

**目标**: 验证模块间交互和数据流

**新增测试场景**（基于UAT反馈）:

| 测试场景 | 测试内容 | 验证点 |
|---------|---------|--------|
| **配置加载集成** | AppContextFactory.create() → EnvManager.load_env() | .env.local正确加载 |
| **nanobot配置构建** | _build_nanobot_config_from_runner() → Config() | 飞书配置正确传递 |
| **通道启动集成** | ChannelManager(config, bus) → FeishuChannel | 通道成功启用 |
| **数据查询集成** | StorageManager.query_by_date_range() → Parquet | 数据去重和过滤正确 |
| **报告生成集成** | ReportService.generate_weekly_report() → AnalyticsEngine | 字段映射正确 |

### 2.3 E2E测试（End-to-End Tests）

**目标**: 验证完整业务流程

**新增E2E测试场景**:

| 测试场景 | 测试流程 | 验证点 |
|---------|---------|--------|
| **完整数据导入流程** | 初始化 → 导入FIT → 查询统计 → 生成报告 | 数据一致性 |
| **Gateway服务启动** | 初始化 → 配置飞书 → 启动gateway → 验证通道 | 通道启用成功 |
| **Agent对话流程** | 初始化 → 配置LLM → 启动agent → 发送查询 | 响应正确 |

---

## 3. 门禁规则

### 3.1 准入规则（测试准入条件）

| 条件 | 要求 | 验证方法 |
|------|------|---------|
| **代码质量** | ruff check 零警告 | `uv run ruff check src/ tests/` |
| **代码格式** | ruff format 零警告 | `uv run ruff format --check src/ tests/` |
| **类型检查** | mypy 无新增错误 | `uv run mypy src/ --ignore-missing-imports` |
| **安全扫描** | bandit 零警告 | `uv run bandit -r src/` |
| **依赖更新** | pyproject.toml 依赖已同步 | `uv sync` |

### 3.2 准出规则（测试通过标准）

| 条件 | 要求 | 验证方法 |
|------|------|---------|
| **单元测试通过率** | 100% | `uv run pytest tests/unit/` |
| **集成测试通过率** | ≥95% | `uv run pytest tests/integration/` |
| **E2E测试通过率** | ≥90% | `uv run pytest tests/e2e/` |
| **代码覆盖率** | core≥80%, agents≥70%, cli≥60% | `uv run pytest --cov=src` |
| **P0级Bug** | 0个 | Bug清单验证 |
| **P1级Bug** | ≤2个 | Bug清单验证 |
| **文档一致性** | 命令与文档100%匹配 | 文档验证脚本 |

### 3.3 上线门禁

| 条件 | 要求 | 验证方法 |
|------|------|---------|
| **P0用例通过率** | 100% | 测试报告 |
| **P1用例通过率** | ≥95% | 测试报告 |
| **致命/严重Bug** | 0个 | Bug清单 |
| **一般Bug修复率** | ≥90% | Bug清单 |
| **核心业务流程** | 全量闭环 | E2E测试报告 |
| **需求验收标准** | 100%满足 | UAT报告 |

---

## 4. 测试用例设计

### 4.1 核心功能测试用例

#### 4.1.1 数据导入测试

| 用例ID | 用例名称 | 前置条件 | 操作步骤 | 预期结果 | 优先级 |
|--------|---------|---------|---------|---------|--------|
| UT-DI-001 | 单文件导入成功 | 有效FIT文件 | 执行data import | 导入成功，显示活动信息 | P0 |
| UT-DI-002 | 批量导入 | 多个FIT文件目录 | 执行data import目录 | 逐个导入，显示进度 | P0 |
| UT-DI-003 | SHA256去重 | 已导入文件 | 再次导入相同文件 | 提示已存在，跳过 | P0 |
| UT-DI-004 | 强制重新导入 | 已导入文件 | 执行data import --force | 覆盖原有数据 | P1 |
| UT-DI-005 | 无效文件处理 | 空文件/损坏文件 | 执行data import | 显示清晰错误，不崩溃 | P1 |

#### 4.1.2 数据查询测试

| 用例ID | 用例名称 | 前置条件 | 操作步骤 | 预期结果 | 优先级 |
|--------|---------|---------|---------|---------|--------|
| UT-DQ-001 | 查看统计数据 | 已导入数据 | 执行data stats | 显示总次数、距离、时长 | P0 |
| UT-DQ-002 | 按年份查询 | 多年度数据 | 执行data stats --year | 仅显示指定年份数据 | P1 |
| UT-DQ-003 | 日期范围查询 | 多日期数据 | 执行data stats --start --end | 仅显示范围内数据 | P1 |
| UT-DQ-004 | 无数据查询 | 无导入数据 | 执行data stats | 显示"暂无数据" | P2 |

#### 4.1.3 数据分析测试

| 用例ID | 用例名称 | 前置条件 | 操作步骤 | 预期结果 | 优先级 |
|--------|---------|---------|---------|---------|--------|
| UT-AN-001 | VDOT趋势分析 | ≥1500m跑步记录 | 执行analysis vdot | 显示VDOT值和趋势 | P0 |
| UT-AN-002 | 训练负荷分析 | 多日跑步记录 | 执行analysis load | 显示TSS/ATL/CTL/TSB | P0 |
| UT-AN-003 | 心率漂移分析 | 含心率数据长距离跑 | 执行analysis hr-drift | 显示漂移率和相关性 | P0 |

#### 4.1.4 配置管理测试

| 用例ID | 用例名称 | 前置条件 | 操作步骤 | 预期结果 | 优先级 |
|--------|---------|---------|---------|---------|--------|
| UT-CM-001 | .env.local加载 | .env.local文件存在 | 启动应用 | 环境变量正确加载 | P0 |
| UT-CM-002 | 配置验证 | 有效config.json | 执行system validate | 验证通过 | P1 |
| UT-CM-003 | 初始化向导 | 无配置文件 | 执行system init | 引导完成配置 | P0 |

#### 4.1.5 报告生成测试

| 用例ID | 用例名称 | 前置条件 | 操作步骤 | 预期结果 | 优先级 |
|--------|---------|---------|---------|---------|--------|
| UT-RP-001 | 生成周报 | 本周跑步记录 | 执行report weekly | 显示本周训练统计 | P0 |
| UT-RP-002 | 生成月报 | 本月跑步记录 | 执行report monthly | 显示本月训练统计 | P0 |
| UT-RP-003 | 报告数据准确性 | 已知数据 | 生成报告 | 数据与实际一致 | P0 |

#### 4.1.6 Gateway服务测试

| 用例ID | 用例名称 | 前置条件 | 操作步骤 | 预期结果 | 优先级 |
|--------|---------|---------|---------|---------|--------|
| UT-GW-001 | 飞书通道配置 | .env.local含飞书配置 | 启动gateway | 显示"已启用通道: feishu" | P0 |
| UT-GW-002 | nanobot配置构建 | 有效LLM配置 | 启动gateway | 配置正确传递给ChannelManager | P0 |
| UT-GW-003 | 通道启动失败处理 | 无效飞书配置 | 启动gateway | 显示清晰错误，不崩溃 | P1 |

### 4.2 边界场景测试用例

| 用例ID | 用例名称 | 测试场景 | 预期结果 | 优先级 |
|--------|---------|---------|---------|--------|
| BT-001 | 超大FIT文件 | 导入>100MB文件 | 正常处理或提示文件大小限制 | P1 |
| BT-002 | 零数据报告 | 无跑步记录生成报告 | 显示"暂无数据"，不报错 | P1 |
| BT-003 | 跨年数据查询 | 查询跨年日期范围 | 正确包含两个年份数据 | P1 |
| BT-004 | 时区边界 | 跨时区FIT文件 | 时间正确处理 | P2 |
| BT-005 | 并发导入 | 同时导入多个文件 | 数据一致性，无冲突 | P2 |

### 4.3 异常场景测试用例

| 用例ID | 用例名称 | 测试场景 | 预期结果 | 优先级 |
|--------|---------|---------|---------|--------|
| ET-001 | 配置文件损坏 | config.json格式错误 | 显示清晰错误，提供修复建议 | P1 |
| ET-002 | .env.local缺失 | 文件不存在 | 使用默认配置或提示 | P1 |
| ET-003 | Parquet文件损坏 | 数据文件损坏 | 跳过损坏文件，继续处理 | P1 |
| ET-004 | 网络异常 | LLM API不可达 | 显示网络错误，不崩溃 | P1 |
| ET-005 | 磁盘空间不足 | 导入时磁盘满 | 显示空间不足错误 | P2 |

---

## 5. 新增测试基础设施

### 5.1 真实数据样本测试

**目的**: 使用真实Parquet数据样本验证查询和报告功能

**实施方法**:
```python
# tests/integration/test_real_data.py
import pytest
from pathlib import Path
from src.core.storage import StorageManager

@pytest.fixture
def real_parquet_path():
    """使用真实Parquet数据样本"""
    return Path.home() / ".nanobot-runner" / "data" / "activities_2024.parquet"

def test_query_with_real_data(real_parquet_path):
    """使用真实数据验证查询"""
    if not real_parquet_path.exists():
        pytest.skip("真实数据不存在")
    
    storage = StorageManager(data_dir=real_parquet_path.parent)
    result = storage.query_by_date_range("2024-01-01", "2024-12-31")
    
    # 验证数据结构和字段
    assert "session_start_time" in result.columns
    assert len(result) > 0
```

### 5.2 第三方库兼容性测试

**目的**: 验证nanobot等第三方库版本变更时的兼容性

**实施方法**:
```python
# tests/integration/test_nanobot_compatibility.py
import pytest
from src.core.provider_adapter import RunnerProviderAdapter

def test_nanobot_config_build():
    """验证nanobot配置构建"""
    try:
        from nanobot.config.loader import Config
        # 测试Config构造函数
        config = Config(
            providers={"default": "openai"},
            agents={"defaults": {"model": "gpt-4o-mini"}},
        )
        assert config is not None
    except ImportError:
        pytest.skip("nanobot未安装")
```

### 5.3 文档一致性验证脚本

**目的**: 验证文档中的CLI命令与实际命令一致

**实施方法**:
```python
# scripts/validate_doc_commands.py
import re
from pathlib import Path
import subprocess

def extract_commands_from_docs():
    """从文档中提取CLI命令"""
    docs_dir = Path("docs")
    commands = []
    
    for md_file in docs_dir.rglob("*.md"):
        content = md_file.read_text()
        # 匹配 uv run nanobotrun 命令
        matches = re.findall(r'uv run nanobotrun\s+[^\n`]+', content)
        commands.extend(matches)
    
    return list(set(commands))

def validate_commands():
    """验证文档命令是否有效"""
    commands = extract_commands_from_docs()
    invalid = []
    
    for cmd in commands:
        result = subprocess.run(
            cmd.split(),
            capture_output=True,
            text=True
        )
        if result.returncode != 0:
            invalid.append((cmd, result.stderr))
    
    return invalid
```

---

## 6. 测试执行计划

### 6.1 测试阶段划分

| 阶段 | 测试类型 | 执行时间 | 负责人 |
|------|---------|---------|--------|
| **阶段1** | 单元测试 | 开发完成后立即执行 | 开发工程师 |
| **阶段2** | 集成测试 | 单元测试通过后执行 | 测试工程师 |
| **阶段3** | E2E测试 | 集成测试通过后执行 | 测试工程师 |
| **阶段4** | UAT测试 | E2E测试通过后执行 | 最终用户/AI Agent |

### 6.2 回归测试策略

**触发条件**:
- Bug修复完成后
- 第三方库版本更新后
- 核心配置逻辑变更后

**回归范围**:
- 修复Bug相关的测试用例
- 受影响模块的集成测试
- 核心业务流程E2E测试

---

## 7. 测试报告输出

### 7.1 轮次测试报告

每轮测试完成后输出，包含：
- 测试范围
- 测试周期
- 测试环境
- 用例执行情况
- 通过率
- Bug统计（按严重等级/模块分类）
- 测试结论
- 剩余风险
- 后续优化建议

### 7.2 全量测试报告

全量测试完成后输出，包含：
- 项目整体质量评级（优秀/良好/合格/不合格）
- 是否符合上线标准
- 完整的质量评估结论
- 上线风险评估
- 上线建议

---

## 8. 质量改进措施

### 8.1 基于UAT反馈的改进

| 改进项 | 改进措施 | 负责人 | 完成时间 |
|--------|---------|--------|---------|
| **配置加载测试** | 增加.env.local加载集成测试 | 测试工程师 | v0.9.5 |
| **第三方库兼容性** | 增加nanobot版本兼容性测试 | 测试工程师 | v0.9.5 |
| **真实数据验证** | 使用真实Parquet样本测试 | 测试工程师 | v0.9.5 |
| **通道配置测试** | 增加飞书通道配置集成测试 | 测试工程师 | v0.9.5 |
| **文档一致性** | 增加文档命令验证脚本 | 测试工程师 | v0.9.5 |

### 8.2 长期改进计划

| 改进项 | 改进措施 | 预计版本 |
|--------|---------|---------|
| **自动化测试覆盖率** | 提升至core≥90%, agents≥80%, cli≥70% | v0.9.6 |
| **性能测试** | 增加大数据量性能测试 | v0.9.6 |
| **安全测试** | 增加安全合规测试 | v0.9.7 |
| **兼容性测试** | 增加多操作系统兼容性测试 | v0.9.7 |

---

## 9. 测试用例清单

### 9.1 用例统计

| 测试类型 | P0用例 | P1用例 | P2用例 | 合计 |
|---------|--------|--------|--------|------|
| 单元测试 | 15 | 10 | 5 | 30 |
| 集成测试 | 10 | 8 | 4 | 22 |
| E2E测试 | 5 | 3 | 2 | 10 |
| **合计** | **30** | **21** | **11** | **62** |

### 9.2 用例执行优先级

**第一轮执行**（P0用例）:
- UT-DI-001, UT-DI-002, UT-DI-003
- UT-DQ-001
- UT-AN-001, UT-AN-002, UT-AN-003
- UT-CM-001, UT-CM-003
- UT-RP-001, UT-RP-002, UT-RP-003
- UT-GW-001, UT-GW-002

**第二轮执行**（P1用例）:
- UT-DI-004, UT-DI-005
- UT-DQ-002, UT-DQ-003
- UT-CM-002
- UT-GW-003
- BT-001, BT-002, BT-003
- ET-001, ET-002, ET-003, ET-004

**第三轮执行**（P2用例）:
- UT-DQ-004
- BT-004, BT-005
- ET-005

---

## 10. 测试环境配置

### 10.1 测试环境要求

| 项目 | 要求 | 验证方法 |
|------|------|---------|
| 操作系统 | Windows 10+/macOS 12+ | 系统信息 |
| Python | 3.11+ | `python --version` |
| uv包管理器 | 已安装 | `uv --version` |
| 磁盘空间 | ≥500MB | `df -h` |
| 网络 | 可选（仅Agent功能需要） | `ping github.com` |

### 10.2 测试数据准备

**方式一：使用项目自带样本数据**
```bash
ls tests/data/fixtures/
```

**方式二：使用真实数据样本**
```bash
# 从~/.nanobot-runner/data/复制Parquet文件到测试目录
cp ~/.nanobot-runner/data/activities_2024.parquet tests/data/real_samples/
```

---

*文档版本: v1.0 | 更新日期: 2026-04-20*
