# Nanobot Runner 文档中心

欢迎来到 Nanobot Runner 项目文档中心。本文档系统采用分层归档策略，为您提供清晰、高效的文档导航体验。

## 📂 文档结构

```
docs/
├── README.md                   # 文档中心首页（本文件）
├── api/                        # API 参考文档
│   ├── analytics_engine.md
│   ├── api_reference.md
│   ├── runner_tools.md
│   └── storage_manager.md
├── architecture/               # 架构设计文档
│   └── 架构设计说明书.md
├── devops/                     # 运维与发布文档
│   ├── release_checklist.md
│   └── 分支管理与发布流程规范.md
├── guides/                     # 使用指南
│   ├── agent_config_guide.md
│   └── cli_usage.md
├── requirements/               # 需求文档
│   └── REQ_需求规格说明书.md
├── history/                    # 版本历史归档
│   ├── VERSION_HISTORY.md
│   ├── v0.4.0/
│   │   └── release_notes.md
│   └── v0.4.3/
│       └── release_notes.md
└── archive/                    # 深度归档（压缩存储）
    ├── bugfix-reports.zip
    ├── development-reports.zip
    ├── test-reports.zip
    ├── v0.1.0-archive.zip
    ├── v0.2.0-archive.zip
    └── v0.3.0-archive.zip
```

## 🚀 快速导航

### 📖 当前版本文档

#### 架构设计
- [架构设计说明书](./architecture/架构设计说明书.md) - 系统整体架构设计

#### API 文档
- [API 参考文档](./api/api_reference.md) - 完整的 API 接口说明
- [数据分析引擎](./api/analytics_engine.md) - Analytics Engine API
- [Runner 工具集](./api/runner_tools.md) - Agent 工具 API
- [存储管理器](./api/storage_manager.md) - Storage Manager API

#### 使用指南
- [CLI 使用指南](./guides/cli_usage.md) - 命令行工具使用说明
- [Agent 配置指南](./guides/agent_config_guide.md) - Agent 配置方法

#### 运维文档
- [分支管理与发布流程规范](./devops/分支管理与发布流程规范.md) - Git 工作流程
- [发布检查清单](./devops/release_checklist.md) - 版本发布检查项

#### 需求文档
- [需求规格说明书](./requirements/REQ_需求规格说明书.md) - 产品需求规格

### 📅 版本历史

- [版本历史汇总](./history/VERSION_HISTORY.md) - 完整的版本发展历程
- [v0.4.3 Release Notes](./history/v0.4.3/release_notes.md) - 最新版本发布说明
- [v0.4.0 Release Notes](./history/v0.4.0/release_notes.md) - v0.4.0 发布说明



### 📦 归档文档

历史版本和临时报告已压缩归档，存储在 `archive/` 目录：

- `development-reports.zip` - 开发报告归档
- `test-reports.zip` - 测试报告归档
- `bugfix-reports.zip` - 修复报告归档
- `v0.1.0-archive.zip` - v0.1.0 版本归档
- `v0.2.0-archive.zip` - v0.2.0 版本归档
- `v0.3.0-archive.zip` - v0.3.0 版本归档

## 🔍 文档分类

### 按角色分类

#### 开发者
- [架构设计说明书](./architecture/架构设计说明书.md)
- [API 参考文档](./api/api_reference.md)
- [分支管理与发布流程规范](./devops/分支管理与发布流程规范.md)

#### 运维人员
- [发布检查清单](./devops/release_checklist.md)
- [分支管理与发布流程规范](./devops/分支管理与发布流程规范.md)

#### 产品经理
- [需求规格说明书](./requirements/REQ_需求规格说明书.md)
- [版本历史汇总](./history/VERSION_HISTORY.md)

#### 用户
- [CLI 使用指南](./guides/cli_usage.md)
- [Agent 配置指南](./guides/agent_config_guide.md)

### 按主题分类

#### 架构与设计
- 架构设计说明书
- API 参考文档
- 数据分析引擎

#### 开发与测试
- 分支管理与发布流程规范
- 发布检查清单
- API 文档

#### 部署与运维
- 发布检查清单
- 分支管理与发布流程规范

## 📊 文档统计

- **当前版本核心文档**: 10 个
- **版本历史文档**: 7 个版本
- **功能特性文档**: 2 个
- **归档压缩包**: 6 个

## 🔗 外部资源

- [项目仓库](https://github.com/yecllsl/nanobot-runner)
- [问题反馈](https://github.com/yecllsl/nanobot-runner/issues)
- [项目 Wiki](https://github.com/yecllsl/nanobot-runner/wiki)

## 📝 文档维护

### 文档更新流程

1. **新增文档**: 在相应目录下创建新文档
2. **更新文档**: 直接修改现有文档内容
3. **归档文档**: 将历史版本文档移动到 archive 目录
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
2. **搜索历史**: 查看版本历史和归档文档
3. **提交问题**: 在 GitHub Issues 中提问
4. **联系团队**: 联系项目维护团队

## 📅 文档更新记录

- **2026-03-30**: 文档系统重构，采用分层归档策略
- **2026-03-28**: v0.4.1 版本文档更新
- **2026-03-25**: v0.4.0 版本文档发布
- **2026-03-20**: v0.3.0 版本文档归档

---

**文档维护团队**: Nanobot Runner 项目组  
**最后更新**: 2026-03-30  
**文档版本**: v2.0