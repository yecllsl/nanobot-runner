# 发布检查清单

## 1. 发布前检查

### 1.1 代码质量检查

- [ ] 执行 `uv run ruff format --check src tests`
- [ ] 执行 `uv run ruff check src tests`
- [ ] 执行 `uv run mypy src --ignore-missing-imports`
- [ ] 执行 `uv run bandit -r src -s B101,B601`
- [ ] 确认无高危安全漏洞

### 1.2 测试验证

- [ ] 执行 `uv run pytest tests/unit/ --cov=src --cov-fail-under=80`
- [ ] 执行 `uv run pytest tests/integration/`
- [ ] 执行 `uv run pytest tests/e2e/`
- [ ] 确认测试通过率100%
- [ ] 确认覆盖率达标（core≥80%, agents≥70%, cli≥60%）

### 1.3 文档更新

- [ ] 更新 `pyproject.toml` 中的版本号
- [ ] 确认版本号符合语义化版本规范
- [ ] 更新 CHANGELOG（如有）

### 1.4 依赖检查

- [ ] 执行 `uv sync --all-extras`
- [ ] 确认依赖版本兼容

## 2. 发布执行

### 2.1 分支管理

#### 2.1.1 团队开发模式
- [ ] 从 develop 分支创建 release 分支
- [ ] 分支命名：`release/vX.Y.Z`
- [ ] 推送 release 分支到远程

#### 2.1.2 单人开发模式（推荐）
- [ ] 直接在 main 分支进行发布准备
- [ ] 确保所有代码已合并到 main 分支
- [ ] 确认 CI 检查全部通过

### 2.2 代码合并

#### 2.2.1 团队开发模式
- [ ] 创建 Release PR（release → main）
- [ ] 至少1名核心开发者审查
- [ ] 确认所有检查通过
- [ ] 使用 `Squash and merge` 或 `Rebase and merge`
- [ ] **禁用** `--delete-branch` 选项

#### 2.2.2 单人开发模式（推荐）
- [ ] 确保 feature 分支已合并到 main
- [ ] 更新 pyproject.toml 版本号
- [ ] 提交版本号变更：`git commit -m "chore: bump version to X.Y.Z"`
- [ ] **关键**：推送 main 分支到远程：`git push origin main`
- [ ] **关键**：等待 CI 检查通过（验证版本号变更正确性）
- [ ] CI 通过后，创建并推送标签触发发布

### 2.3 标签管理

**前置条件**：确保 main 分支已推送到远程且 CI 检查通过

- [ ] 切换到 main 分支：`git checkout main`
- [ ] 拉取最新代码：`git pull origin main`
- [ ] **验证**：确认 CI Pipeline 已通过（`gh run list --limit 1`）
- [ ] 创建标签：`git tag -a vX.Y.Z -m "Release vX.Y.Z"`
- [ ] 推送标签：`git push origin vX.Y.Z`

### 2.4 热修复发布注意事项

#### 2.4.1 避免发布时机问题
- [ ] **关键**：确保修复代码已合并到 main 分支后再创建标签
- [ ] **禁止**：在 PR 合并前推送标签（会导致发布包不完整）
- [ ] **验证**：确认 pyproject.toml 中的版本号与标签一致

#### 2.4.2 发布时机检查清单
- [ ] **关键**：确保修复代码已合并到 main 分支
- [ ] **验证**：pyproject.toml 版本号与标签一致
- [ ] **禁止**：在 PR 合并前推送标签
- [ ] **确认**：CI 检查全部通过

#### 2.4.3 紧急修复流程
- [ ] 创建 hotfix 分支：`git checkout -b hotfix/issue-description main`
- [ ] 修复问题并提交
- [ ] 推送分支：`git push origin hotfix/issue-description`
- [ ] 等待 CI 检查通过
- [ ] 合并到 main 分支
- [ ] **然后**创建发布标签

## 3. 发布后验证

### 3.1 CI/CD 流程监控

- [ ] 监控 release.yml workflow 执行状态
- [ ] 确认构建成功（绿色状态）
- [ ] 访问 GitHub Releases 页面确认包文件正常上传
- [ ] **验证**：确认发布包包含所有修复代码

### 3.2 环境同步

#### 3.2.1 团队开发模式
- [ ] 切换到 develop 分支：`git checkout develop`
- [ ] 同步 main 分支内容：`git merge main`
- [ ] 推送更新：`git push origin develop`

#### 3.2.2 单人开发模式（推荐）
- [ ] **跳过**：无需同步 develop 分支（简化流程）
- [ ] 确保所有功能分支基于最新的 main 分支

### 3.3 版本验证

- [ ] 安装测试：`pip install nanobot-runner==vX.Y.Z`
- [ ] 功能验证：执行关键命令确认修复生效
- [ ] 回滚准备：记录发布前版本号，便于紧急回滚

## 4. 紧急情况处理

### 4.1 发布回滚

**回滚条件**：生产环境严重问题、安全漏洞暴露、数据丢失风险

**回滚步骤**：
1. 创建 hotfix 分支：`git checkout -b hotfix/rollback-vX.Y.Z main`
2. 回滚代码变更
3. 创建紧急发布标签
4. 执行紧急发布流程

### 4.2 热修复发布问题处理

#### 4.2.1 发布时机错误（v0.4.4 案例）
**问题**：标签在 PR 合并前推送，导致发布包不完整
**解决方案**：
1. 发布修复版本（如 v0.4.5）
2. 更新文档说明推荐使用修复版本
3. 通知用户避免使用有问题的版本

#### 4.2.2 分支保护冲突
**问题**：单人开发场景下，PR 审查要求阻碍紧急修复
**解决方案**：
1. 调整分支保护设置，禁用 PR 审查要求
2. 保留 CI 检查作为质量门禁
3. 启用管理员绕过权限

### 4.3 问题响应

| 问题级别 | 响应时间 | 处理方式 |
|---------|---------|---------|
| 严重问题 | 30分钟内响应 | 立即发布热修复版本 |
| 一般问题 | 2小时内响应 | 下一个常规版本修复 |
| 功能请求 | 24小时内评估 | 排入开发计划 |

## 5. 本地预检查脚本

```bash
# 完整预检查
uv run ruff format --check src/ tests/
uv run ruff check src/ tests/
uv run mypy src/ --ignore-missing-imports
uv run bandit -r src/ -s B101,B601
uv run pytest tests/unit/ --cov=src --cov-fail-under=80
```

---

**文档版本**: v0.7.0  
**最后更新**: 2026-04-11  
**关联文档**: [分支管理与发布流程规范](./分支管理与发布流程规范.md)  
**更新说明**: 更新为使用ruff进行代码质量检查
