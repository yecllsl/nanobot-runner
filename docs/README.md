# 项目文档索引

> 最后更新: 2026-03-07  
> 文档总数: 45个

---

## 文档命名规范

```
{角色}_{指令}_v{版本号}.md    # 版本迭代文档
{角色}_{指令}.md              # 通用文档
```

**角色缩写对照表**:
| 缩写 | 角色 | 目录 |
|------|------|------|
| ARC | 架构师 | architecture/ |
| DEV | 开发 | development/ |
| TST | 测试 | test/ |
| OPS | 运维 | devops/ |
| REQ | 需求 | requirement/ |
| PLN | 规划 | planning/ |
| EXT | 外部 | external/ |

---

## 一、架构文档 (architecture/)

### 1.1 架构设计
| 文档 | 说明 |
|------|------|
| [ARC_架构设计.md](architecture/ARC_架构设计.md) | 系统架构设计文档 |

### 1.2 版本迭代架构
| 文档 | 版本 | 说明 |
|------|------|------|
| [0.2.0/迭代架构设计说明书.md](architecture/0.2.0/迭代架构设计说明书.md) | v0.2.0 | 0.2.0版本架构设计 |
| [0.3.0/迭代架构设计说明书.md](architecture/0.3.0/迭代架构设计说明书.md) | v0.3.0 | 0.3.0版本架构设计 |

### 1.3 架构评审
| 文档 | 版本 | 说明 |
|------|------|------|
| [ARC_架构符合性评审报告.md](architecture/review/ARC_架构符合性评审报告.md) | - | 通用架构评审 |
| [ARC_v0.2.0_架构符合性评审报告.md](architecture/review/ARC_v0.2.0_架构符合性评审报告.md) | v0.2.0 | 架构评审报告 |
| [ARC_v0.2.0_架构符合性评审报告_复审.md](architecture/review/ARC_v0.2.0_架构符合性评审报告_复审.md) | v0.2.0 | 架构评审复审 |
| [ARC-05_风险复盘_v0.2.0.md](architecture/review/ARC-05_风险复盘_v0.2.0.md) | v0.2.0 | 风险复盘报告 |

---

## 二、开发文档 (development/)

### 2.1 交付报告
| 文档 | 版本 | 说明 |
|------|------|------|
| [DEV_交付报告.md](development/DEV_交付报告.md) | - | 通用交付报告 |
| [DEV_v0.2.0_交付报告_en.md](development/DEV_v0.2.0_交付报告_en.md) | v0.2.0 | 英文交付报告 |
| [DEV_单元测试报告.md](development/DEV_单元测试报告.md) | - | 单元测试报告 |
| [DEV_测试报告_en.md](development/DEV_测试报告_en.md) | - | 英文测试报告 |

### 2.2 Bug修复报告
| 文档 | 说明 |
|------|------|
| [DEV_20240304_Bug修复报告.md](development/bug_fix/DEV_20240304_Bug修复报告.md) | Bug修复报告 |
| [DEV_v0.2.0_Bug修复报告.md](development/bug_fix/DEV_v0.2.0_Bug修复报告.md) | v0.2.0 Bug修复 |
| [DEV_v0.2.0_Bug修复报告_回归.md](development/bug_fix/DEV_v0.2.0_Bug修复报告_回归.md) | Bug修复回归 |

### 2.3 调试报告
| 文档 | 说明 |
|------|------|
| [DEV_本地调试报告.md](development/debug/DEV_本地调试报告.md) | 本地调试报告 |

---

## 三、运维文档 (devops/)

### 3.1 配置与规范
| 文档 | 说明 |
|------|------|
| [OPS_CICD流水线配置说明.md](devops/OPS_CICD流水线配置说明.md) | CICD配置说明 |
| [OPS_Git分支与发布流程规范.md](devops/OPS_Git分支与发布流程规范.md) | Git流程规范 |
| [OPS_项目部署手册.md](devops/OPS_项目部署手册.md) | 部署手册 |

### 3.2 运维报告
| 文档 | 版本 | 说明 |
|------|------|------|
| [OPS-02_CICD流水线验证_v0.2.0.md](devops/OPS-02_CICD流水线验证_v0.2.0.md) | v0.2.0 | CICD验证 |
| [OPS-04_自动化发布报告_v0.2.0.md](devops/OPS-04_自动化发布报告_v0.2.0.md) | v0.2.0 | 自动化发布 |
| [OPS-05_运维文档更新报告_v0.2.0.md](devops/OPS-05_运维文档更新报告_v0.2.0.md) | v0.2.0 | 文档更新 |

### 3.3 版本发布
| 文档 | 版本 | 说明 |
|------|------|------|
| [OPS_v0.1.0_版本发布报告.md](devops/release_notes/OPS_v0.1.0_版本发布报告.md) | v0.1.0 | 版本发布报告 |

### 3.4 故障排查
| 文档 | 说明 |
|------|------|
| [GitHub_Actions代码质量故障排查报告.md](devops/troubleshoot/GitHub_Actions代码质量故障排查报告.md) | 代码质量故障 |
| [GitHub_Actions代码质量检查工具执行故障排查报告.md](devops/troubleshoot/GitHub_Actions代码质量检查工具执行故障排查报告.md) | 工具执行故障 |
| [GitHub_Actions代码质量检查工具配置故障排查报告.md](devops/troubleshoot/GitHub_Actions代码质量检查工具配置故障排查报告.md) | 工具配置故障 |
| [GitHub_Actions流水线故障排查报告.md](devops/troubleshoot/GitHub_Actions流水线故障排查报告.md) | 流水线故障 |
| [GitHub_Actions流水线故障排查报告_v2.md](devops/troubleshoot/GitHub_Actions流水线故障排查报告_v2.md) | 流水线故障v2 |

---

## 四、规划文档 (planning/)

### 4.1 任务清单
| 文档 | 版本 | 说明 |
|------|------|------|
| [PLN_开发任务清单.md](planning/PLN_开发任务清单.md) | - | 通用任务清单 |
| [PLN_v0.2.0_任务清单.md](planning/PLN_v0.2.0_任务清单.md) | v0.2.0 | 版本任务清单 |
| [PLN_v0.3.0_任务清单.md](planning/PLN_v0.3.0_任务清单.md) | v0.3.0 | 版本任务清单 |

### 4.2 准备报告
| 文档 | 版本 | 说明 |
|------|------|------|
| [PLN_v0.3.0_开发准备报告.md](planning/PLN_v0.3.0_开发准备报告.md) | v0.3.0 | 开发准备报告 |

---

## 五、需求文档 (requirement/)

### 5.1 需求规格说明书
| 文档 | 说明 |
|------|------|
| [REQ_需求规格说明书.md](requirement/REQ_需求规格说明书.md) | 中文需求规格 |
| [REQ_需求规格说明书_en.md](requirement/REQ_需求规格说明书_en.md) | 英文需求规格 |

### 5.2 版本迭代需求
| 文档 | 版本 | 说明 |
|------|------|------|
| [0.2.0/迭代需求规格说明书.md](requirement/0.2.0/迭代需求规格说明书.md) | v0.2.0 | 迭代需求 |
| [0.3.0/迭代需求规格说明书.md](requirement/0.3.0/迭代需求规格说明书.md) | v0.3.0 | 迭代需求 |

---

## 六、测试文档 (test/)

### 6.1 测试策略与规范
| 文档 | 说明 |
|------|------|
| [TST_测试策略与规范.md](test/TST_测试策略与规范.md) | 测试策略规范 |
| [TST_目录结构规范.md](test/TST_目录结构规范.md) | 目录结构规范 |
| [TST_文档模板库.md](test/TST_文档模板库.md) | 文档模板库 |
| [TST_v0.2.0_测试策略.md](test/TST_v0.2.0_测试策略.md) | v0.2.0测试策略 |

### 6.2 测试用例
| 文档 | 版本 | 说明 |
|------|------|------|
| [TST_v0.2.0_Agent自然语言交互测试用例.md](test/cases/TST_v0.2.0_Agent自然语言交互测试用例.md) | v0.2.0 | Agent交互测试 |

### 6.3 测试报告
| 文档 | 版本 | 说明 |
|------|------|------|
| [TST_v0.2.0_Bug清单.md](test/reports/TST_v0.2.0_Bug清单.md) | v0.2.0 | Bug清单 |
| [TST_v0.2.0_全量测试报告.md](test/reports/TST_v0.2.0_全量测试报告.md) | v0.2.0 | 全量测试 |
| [TST_v0.2.0_回归测试报告.md](test/reports/TST_v0.2.0_回归测试报告.md) | v0.2.0 | 回归测试 |
| [TST_v0.2.0_迭代质量评估报告.md](test/reports/TST_v0.2.0_迭代质量评估报告.md) | v0.2.0 | 质量评估 |

### 6.4 性能测试
| 文档 | 说明 |
|------|------|
| [TST_20240304_查询性能测试报告.md](test/performance/TST_20240304_查询性能测试报告.md) | 查询性能测试 |

### 6.5 回归测试
| 文档 | 说明 |
|------|------|
| [TST_20240304_Bug回归测试报告.md](test/regression/TST_20240304_Bug回归测试报告.md) | Bug回归测试 |

---

## 七、外部文档 (external/)

### 7.1 教程文档
| 文档 | 说明 |
|------|------|
| [示范项目主要目录作用说明.md](external/tutorials/示范项目主要目录作用说明.md) | 目录说明 |
| [EXT_Python_Rust_PyO3项目规范.md](external/tutorials/EXT_Python_Rust_PyO3项目规范.md) | PyO3项目规范 |
| [EXT_Python_Rust_PyO3架构规范_代码分层.md](external/tutorials/EXT_Python_Rust_PyO3架构规范_代码分层.md) | 代码分层规范 |
| [EXT_调用外部工具教程.md](external/tutorials/EXT_调用外部工具教程.md) | 外部工具教程 |

---

## 快速导航

### 按版本查找

**v0.2.0 文档**:
- [架构设计](architecture/0.2.0/迭代架构设计说明书.md)
- [需求规格](requirement/0.2.0/迭代需求规格说明书.md)
- [任务清单](planning/PLN_v0.2.0_任务清单.md)
- [测试报告](test/reports/TST_v0.2.0_全量测试报告.md)

**v0.3.0 文档**:
- [架构设计](architecture/0.3.0/迭代架构设计说明书.md)
- [需求规格](requirement/0.3.0/迭代需求规格说明书.md)
- [任务清单](planning/PLN_v0.3.0_任务清单.md)
- [开发准备报告](planning/PLN_v0.3.0_开发准备报告.md)

### 按角色查找

| 角色 | 文档目录 |
|------|----------|
| 架构师 | [architecture/](architecture/) |
| 开发 | [development/](development/) |
| 测试 | [test/](test/) |
| 运维 | [devops/](devops/) |
| 需求 | [requirement/](requirement/) |
| 规划 | [planning/](planning/) |
