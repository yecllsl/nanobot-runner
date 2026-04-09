# Nanobot Runner 文档中心

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
│   └── 架构设计说明书.md        # 系统整体架构设计
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
├── requirements/               # 需求文档
│   └── REQ_需求规格说明书.md    # 产品需求规格
├── test/                       # 测试文档
│   └── 全量测试用例清单.md      # 测试用例清单
└── archive/                    # 版本归档（压缩存储）
    ├── README.md               # 归档索引
    ├── v0.9.0-archive.zip      # v0.9.0 版本归档
    ├── v0.8.0-archive.zip      # v0.8.0 版本归档
    ├── v0.6.0-archive.zip      # v0.6.0 版本归档
    ├── Sprint2-archive.zip     # Sprint2 迭代归档
    └── v0.2.0-archive.zip      # v0.2.0 版本归档
```

## 🚀 快速导航

### 📖 当前版本文档 (v0.9.0)

#### 架构设计
- [架构设计说明书](./architecture/架构设计说明书.md) - 系统整体架构设计（v0.9.0重构）

#### API 文档
- [API 参考文档](./api/api_reference.md) - 完整的 API 接口说明
- [数据分析引擎](./api/analytics_engine.md) - Analytics Engine API
- [Runner 工具集](./api/runner_tools.md) - Agent 工具 API
- [存储管理器](./api/storage_manager.md) - Storage Manager API

#### 使用指南
- [CLI 使用指南](./guides/cli_usage.md) - 命令行工具使用说明（v0.9.0 CLI分层）
- [Agent 配置指南](./guides/agent_config_guide.md) - Agent 配置方法
- [Agent 工具扩展指南](./guides/agent_tools_guide.md) - 新增工具步骤
- [开发指南](./guides/development_guide.md) - Polars 规范、异常处理、类型注解
- [测试指南](./guides/testing_guide.md) - Mock 策略、测试数据、隐私红线
- [故障排查指南](./guides/troubleshooting.md) - 常见问题解决方案

#### 运维文档
- [分支管理与发布流程规范](./devops/分支管理与发布流程规范.md) - Git 工作流程
- [发布检查清单](./devops/release_checklist.md) - 版本发布检查项

#### 需求文档
- [需求规格说明书](./requirements/REQ_需求规格说明书.md) - 产品需求规格

#### 测试文档
- [全量测试用例清单](./test/全量测试用例清单.md) - 测试用例清单

### 📦 归档文档

历史版本文档已压缩归档，存储在 `archive/` 目录：

- [归档索引](./archive/README.md) - 完整的归档文档索引
- `v0.9.0-archive.zip` - v0.9.0 版本归档（架构重构、依赖注入、CLI分层）
- `v0.8.0-archive.zip` - v0.8.0 版本归档（训练计划、飞书日历）
- `v0.6.0-archive.zip` - v0.6.0 版本归档（训练计划基础功能）
- `Sprint2-archive.zip` - Sprint2 迭代归档（ProfileEngine拆分、CLI拆分）
- `v0.2.0-archive.zip` - v0.2.0 版本归档（Agent交互、E2E测试）

## 🔍 文档分类

### 按角色分类

#### 开发者
- [架构设计说明书](./architecture/架构设计说明书.md) - 系统架构设计
- [API 参考文档](./api/api_reference.md) - API 接口说明
- [开发指南](./guides/development_guide.md) - 开发规范
- [测试指南](./guides/testing_guide.md) - 测试策略
- [分支管理与发布流程规范](./devops/分支管理与发布流程规范.md) - Git 工作流程

#### 运维人员
- [发布检查清单](./devops/release_checklist.md) - 发布检查项
- [分支管理与发布流程规范](./devops/分支管理与发布流程规范.md) - 发布流程
- [故障排查指南](./guides/troubleshooting.md) - 故障排查

#### 产品经理
- [需求规格说明书](./requirements/REQ_需求规格说明书.md) - 产品需求
- [归档索引](./archive/README.md) - 版本历史

#### 用户
- [CLI 使用指南](./guides/cli_usage.md) - CLI 使用说明
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

- **当前版本核心文档**: 16 个
- **归档版本**: 5 个版本
- **指南文档**: 6 个
- **API 文档**: 4 个

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
