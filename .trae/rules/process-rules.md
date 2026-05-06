---
alwaysApply: false
description: 流程规则：分支策略、发布准入、变更记录（单人开发模式）
---
# 流程规则

## 分支策略（单人模式）
- 禁止在未完成功能时推送Tag
- 禁止跳过CI检查直接发布
- Commit格式必须遵循：`<type>(<scope>): <subject>`
- feature分支可选：小改动可直接在main开发，大功能建议用feature分支

## 发布准入（单人模式）
- 版本号必须保持一致（pyproject.toml/README.md/CHANGELOG.md）
- 版本号更新后必须先推送main，等待CI通过后再创建Tag
- 禁止在CI未通过时创建Tag
- 回归报告可选：小版本更新可跳过，大版本更新建议保留

## 变更记录
- 版本发布必须更新CHANGELOG.md
- 版本号必须保持pyproject.toml/README.md/CHANGELOG.md一致
- 发布报告保存路径：`docs/devops/发布报告_{版本号}.md`
