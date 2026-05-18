# Nanobot Runner 文档中心

> **文档版本**: v0.22.0 | **更新日期**: 2026-05-18
> **当前基线**: v0.22.0

欢迎来到 Nanobot Runner 项目文档中心。本文档系统采用分层归档策略，为您提供清晰、高效的文档导航体验。

## 📂 文档结构

```
docs/
├── README.md                   # 文档中心首页（本文件）
├── api/                        # API 参考文档
│   ├── analytics_engine.md     # 数据分析引擎 API
│   ├── api_reference.md        # 完整 API 参考
│   ├── runner_tools.md         # Agent 工具 API
│   └── storage_manager.md      # 存储管理器 API
├── architecture/               # 架构设计文档
│   └── 架构设计说明书.md        # 系统整体架构设计 (v9.2.0)
├── devops/                     # 运维与发布文档
│   ├── release_checklist.md    # 发布检查清单
│   └── 分支管理与发布流程规范.md # Git 工作流程
├── guides/                     # 使用指南
│   ├── agent_config_guide.md   # Agent 配置指南
│   ├── agent_tools_guide.md    # Agent 工具扩展指南
│   ├── cli_usage.md            # CLI 使用指南
│   ├── development_guide.md    # 开发指南
│   ├── testing_guide.md        # 测试指南
│   └── troubleshooting.md      # 故障排查指南
├── product/                    # 产品规划文档
│   └── 产品规划方案.md          # 产品路线图与规划 (v9.2)
├── requirements/               # 需求文档
│   └── REQ_需求规格说明书.md    # 产品需求规格 (v8.6)
├── test/                       # 测试文档
│   ├── 用户验收测试指南.md      # UAT测试指南
│   ├── uat_test_cases/         # UAT测试用例
│   └── test_templates/         # 测试模板
├── review/                     # 评审报告
│   └── code-review-report-*.md # 代码评审报告
└── archive/                    # 版本归档（压缩存储）
    └── README.md               # 归档索引
```

## 🚀 快速导航

### 📖 当前版本文档 (v0.22.0)

#### 架构设计
- [架构设计说明书](./architecture/架构设计说明书.md) - 系统整体架构设计（v9.2.0）

#### 产品规划
- [产品规划方案](./product/产品规划方案.md) - 产品路线图与版本规划（v9.2）

#### API 文档
- [API 参考文档](./api/api_reference.md) - 完整的 API 接口说明（v0.22.0）
- [数据分析引擎](./api/analytics_engine.md) - Analytics Engine API
- [Runner 工具集](./api/runner_tools.md) - Agent 工具 API
- [存储管理器](./api/storage_manager.md) - Storage Manager API

#### 使用指南
- [CLI 使用指南](./guides/cli_usage.md) - 命令行工具使用说明（v0.22.0）
- [Agent 配置指南](./guides/agent_config_guide.md) - Agent 配置方法
- [Agent 工具扩展指南](./guides/agent_tools_guide.md) - 新增工具步骤
- [开发指南](./guides/development_guide.md) - Polars 规范、异常处理、类型注解
- [测试指南](./guides/testing_guide.md) - Mock 策略、测试数据、隐私红线
- [故障排查指南](./guides/troubleshooting.md) - 常见问题解决方案

#### 运维文档
- [分支管理与发布流程规范](./devops/分支管理与发布流程规范.md) - Git 工作流程
- [发布检查清单](./devops/release_checklist.md) - 版本发布检查项

#### 需求文档
- [需求规格说明书](./requirements/REQ_需求规格说明书.md) - 产品需求规格（v8.6）

#### 测试文档
- [用户验收测试指南](./test/用户验收测试指南.md) - UAT测试指南
- [UAT测试用例](./test/uat_test_cases/) - 各模块UAT测试用例
- [测试模板](./test/test_templates/) - 测试文档模板

### 📦 归档文档

历史版本文档已归档，存储在 `archive/` 目录：

- [归档索引](./archive/README.md) - 完整的归档文档索引

## 🔍 文档分类

### 按角色分类

#### 开发者
- [架构设计说明书](./architecture/架构设计说明书.md) - 系统架构设计（v9.2.0）
- [产品规划方案](./product/产品规划方案.md) - 产品路线图（v9.2）
- [API 参考文档](./api/api_reference.md) - API 接口说明（v0.22.0）
- [开发指南](./guides/development_guide.md) - 开发规范
- [测试指南](./guides/testing_guide.md) - 测试策略
- [分支管理与发布流程规范](./devops/分支管理与发布流程规范.md) - Git 工作流程

#### 运维人员
- [发布检查清单](./devops/release_checklist.md) - 发布检查项
- [分支管理与发布流程规范](./devops/分支管理与发布流程规范.md) - 发布流程
- [故障排查指南](./guides/troubleshooting.md) - 故障排查

#### 产品经理
- [需求规格说明书](./requirements/REQ_需求规格说明书.md) - 产品需求（v8.6）
- [产品规划方案](./product/产品规划方案.md) - 产品路线图（v9.2）
- [用户验收测试指南](./test/用户验收测试指南.md) - UAT测试指南
- [归档索引](./archive/README.md) - 版本历史

#### 用户
- [CLI 使用指南](./guides/cli_usage.md) - CLI 使用说明（v0.22.0）
- [Agent 配置指南](./guides/agent_config_guide.md) - Agent 配置
- [故障排查指南](./guides/troubleshooting.md) - 常见问题

### 按主题分类

#### 架构与设计
- 架构设计说明书
- API 参考文档
- 数据分析引擎

#### 开发与测试
- 开发指南
- 测试指南
- Agent 工具扩展指南
- API 文档

#### 部署与运维
- 发布检查清单
- 分支管理与发布流程规范
- 故障排查指南

## 📊 文档统计

- **当前基线**: v0.22.0
- **核心文档**: 18 个
- **UAT测试用例**: 12 个模块
- **指南文档**: 6 个
- **API 文档**: 4 个

## 📋 版本功能速览

| 版本 | 核心功能 | 状态 |
|------|----------|------|
| v0.18 | 数据可视化与导出 | ✅ 已完成 |
| v0.19 | 身体信号分析(HRV/疲劳度/恢复) | ✅ 已完成 |
| v0.20 | ML增强预测(VDOT/比赛/伤病) | ✅ 已完成 |
| v0.21 | 数字孪生引擎(What-If推演) | ✅ 已完成 |
| v0.22 | 多视角验证(条件性)/质量收口 | ✅ 当前基线 |
| v0.23 | 决策追踪与结果回填 | 📋 规划中 |
| v0.24 | 个性化学习 | 📋 规划中 |
| v0.25 | 自适应进化引擎 | 📋 规划中 |

## 🔗 外部资源

- [项目仓库](https://github.com/yecllsl/nanobot-runner)
- [问题反馈](https://github.com/yecllsl/nanobot-runner/issues)
- [项目 Wiki](https://github.com/yecllsl/nanobot-runner/wiki)

## 📝 文档维护

### 文档更新流程

1. **新增文档**: 在相应目录下创建新文档
2. **更新文档**: 直接修改现有文档内容
3. **归档文档**: 将历史版本文档移动到 archive 目录并压缩
4. **更新索引**: 修改本 README.md 文件

### 文档命名规范

- 使用中文命名，便于理解
- 采用描述性名称，避免缩写
- 版本相关文档包含版本号

### 文档格式规范

- 使用 Markdown 格式
- 包含清晰的标题层级
- 添加必要的代码示例
- 提供相关文档链接

## 🆘 获取帮助

如果您在使用过程中遇到问题：

1. **查阅文档**: 首先查看相关文档章节
2. **搜索归档**: 查看归档文档中的历史版本
3. **提交问题**: 在 GitHub Issues 中提问
4. **联系团队**: 联系项目维护团队

## 📅 文档更新记录

- **2026-04-09**: v0.9.0 版本文档更新，架构重构、依赖注入、CLI分层
- **2026-03-15**: v0.8.0 版本文档更新，训练计划、飞书日历
- **2026-03-10**: v0.6.0 版本文档更新，训练计划基础功能
- **2026-03-08**: Sprint2 迭代文档归档
- **2026-03-06**: v0.2.0 版本文档归档

---

**文档维护团队**: Nanobot Runner 项目组  
**最后更新**: 2026-04-09  
**文档版本**: v3.0
