---
alwaysApply: false
description: 流程规则：调用技能进行分析设计开发测试发布等流程操作时调用本规则。
---
# 流程规则

## 分支策略（单人模式）
- 禁止在未完成功能时推送Tag
- 禁止跳过CI检查直接发布
- Commit格式必须遵循：`<type>(<scope>): <subject>`
- feature分支可选：小改动可直接在main开发，大功能建议用feature分支

## 开发流程（嵌入全局方法论）
- 功能开发必须遵循TDD循环：先写失败测试 → 写实现 → 重构
- Bug根因不明时，必须先执行systematic-debugging定位根因，禁止盲目修改
- 每次commit前必须运行验证命令（lint/test/typecheck），拿证据
- 声称完成必须有验证证据，禁止"应该没问题"式声称
- 需求不明确时，必须先brainstorming澄清，禁止直接编码

## 发布准入（单人模式）
- 版本号必须保持一致（pyproject.toml/README.md/CHANGELOG.md）
- 版本号更新后必须先推送main，等待CI通过后再创建Tag
- 禁止在CI未通过时创建Tag
- 回归报告可选：小版本更新可跳过，大版本更新建议保留

## 变更记录
- 版本发布必须更新CHANGELOG.md
- 版本号必须保持pyproject.toml/README.md/CHANGELOG.md一致
- 发布报告保存路径：`docs/devops/发布报告_{版本号}.md`
