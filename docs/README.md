# 项目文档导航

本文档提供 Nanobot Runner 项目的完整文档索引，帮助您快速定位所需信息。

## 📚 文档分类

### 核心文档

| 文档 | 说明 | 位置 |
|------|------|------|
| **项目说明** | 项目简介、快速开始、功能介绍 | [README.md](../README.md) |
| **Agent 工作指南** | 开发命令、架构细节、开发注意事项 | [AGENTS.md](../AGENTS.md) |
| **CLI 使用指南** | 完整命令行使用说明 | [CLI Usage](./guides/cli_usage.md) |

### API 参考文档

| 模块 | 说明 |
|------|------|
| [AnalyticsEngine](./api/analytics_engine.md) | 数据分析引擎（VDOT/TSS/心率漂移/训练负荷） |
| [StorageManager](./api/storage_manager.md) | Parquet 存储管理器 |
| [RunnerTools](./api/runner_tools.md) | Agent 工具集 |

### 架构设计

| 文档 | 说明 |
|------|------|
| [架构设计总览](./architecture/ARC_架构设计.md) | 项目整体架构设计 |
| [v0.3.0 架构评审](./architecture/review/ARC_v0.3.0_架构符合性评审报告.md) | 最新版架构符合性评审 |

### 需求规格

| 文档 | 说明 |
|------|------|
| [需求规格说明书](./requirement/REQ_需求规格说明书.md) | 主需求文档 |
| [v0.3.0 迭代需求](./requirement/0.3.0/迭代需求规格说明书.md) | 当前迭代需求 |

### 开发文档

| 文档 | 说明 |
|------|------|
| [v0.3.0 交付报告](./development/DEV_v0.3.0_交付报告.md) | 最新版开发交付报告 |

### 测试文档

| 文档 | 说明 |
|------|------|
| [v0.3.0 回归测试与质量评估](./test/TST_v0.3.0_回归测试与质量评估报告.md) | 最新版测试报告 |
| [性能基准测试](./test/performance/TST_v0.3.0_性能基准测试报告.md) | 性能测试结果 |

### 运维文档

| 文档 | 说明 |
|------|------|
| [项目部署手册](./devops/OPS_项目部署手册.md) | 部署指南 |
| [CICD 流水线配置](./devops/OPS_CICD 流水线配置说明.md) | CI/CD 配置说明 |
| [版本发布说明](./devops/release_notes/release.md) | 所有版本发布记录 |

### 规划文档

| 文档 | 说明 |
|------|------|
| [v0.3.0 任务清单](./planning/PLN_v0.3.0_任务清单.md) | 当前迭代任务规划 |

## 📁 文档目录结构

```
docs/
├── README.md                 # 📍 本文档
├── api/                      # API 参考文档
│   ├── analytics_engine.md
│   ├── storage_manager.md
│   └── runner_tools.md
├── guides/                   # 用户指南
│   └── cli_usage.md
├── architecture/             # 架构设计
│   ├── ARC_架构设计.md
│   └── review/
│       └── ARC_v0.3.0_架构符合性评审报告.md
├── requirement/              # 需求规格
│   ├── REQ_需求规格说明书.md
│   └── 0.3.0/
│       └── 迭代需求规格说明书.md
├── planning/                 # 任务规划
│   └── PLN_v0.3.0_任务清单.md
├── development/              # 开发报告
│   └── DEV_v0.3.0_交付报告.md
├── test/                     # 测试报告
│   ├── TST_v0.3.0_回归测试与质量评估报告.md
│   └── performance/
│       └── TST_v0.3.0_性能基准测试报告.md
├── devops/                   # 运维文档
│   ├── OPS_项目部署手册.md
│   ├── OPS_CICD 流水线配置说明.md
│   └── release_notes/
│       └── release.md
└── archive/                  # 历史归档
    ├── v0.1.0/
    └── v0.2.0/
```

## 🏷️ 版本历史

| 版本 | 发布日期 | 说明 | 文档位置 |
|------|---------|------|---------|
| **v0.3.0** | 2026-03-17 | 训练负荷完整实现与智能晨报 | [当前版本](#) |
| v0.2.0 | 2024-03-04 | Agent 自然语言交互完善 | [归档](./archive/v0.2.0/) |
| v0.1.0 | 2024-02-01 | 基础功能实现 | [归档](./archive/v0.1.0/) |

## 🔍 快速检索

### 按主题查找

- **数据导入**: [CLI 使用指南 - import 命令](./guides/cli_usage.md#import-命令)
- **数据分析**: [AnalyticsEngine API](./api/analytics_engine.md)
- **Agent 工具**: [RunnerTools API](./api/runner_tools.md)
- **飞书推送**: [项目部署手册 - 飞书配置](./devops/OPS_项目部署手册.md#飞书推送配置)
- **CI/CD**: [CICD 流水线配置](./devops/OPS_CICD 流水线配置说明.md)

### 按角色查找

**开发者**:
1. [AGENTS.md](../AGENTS.md) - 开发环境配置
2. [CLI 使用指南](./guides/cli_usage.md) - 本地调试
3. [API 参考](#api-参考文档) - 接口文档

**测试工程师**:
1. [测试报告](#测试文档) - 测试策略与结果
2. [AGENTS.md - 测试命令](../AGENTS.md#常用命令) - 测试执行

**运维工程师**:
1. [项目部署手册](./devops/OPS_项目部署手册.md) - 部署指南
2. [CICD 流水线配置](./devops/OPS_CICD 流水线配置说明.md) - 发布流程
3. [版本发布说明](./devops/release_notes/release.md) - 发布记录

## 📊 文档统计

- **总文档数**: ~75 个（已归档历史版本）
- **核心文档**: 15 个
- **API 文档**: 3 个
- **测试文档**: 5 个
- **运维文档**: 8 个

## 📝 文档维护

### 文档更新规范

1. **新增功能**: 同步更新 API 文档和用户指南
2. **版本迭代**: 创建新版本目录，旧版本归档到 `archive/`
3. **文档修订**: 更新文档顶部版本号

### 文档生命周期

```
新建 → 审核 → 发布 → 维护 → 归档
```

---

**最后更新**: 2026-03-17  
**当前版本**: v0.3.0  
**维护者**: 项目团队
