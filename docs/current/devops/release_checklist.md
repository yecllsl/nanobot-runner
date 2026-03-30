# 发布检查清单

## 1. 发布前检查

### 1.1 代码质量检查

- [ ] 执行 `uv run black src tests --check`
- [ ] 执行 `uv run isort src tests --check-only`
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

- [ ] 从 develop 分支创建 release 分支
- [ ] 分支命名：`release/vX.Y.Z`
- [ ] 推送 release 分支到远程

### 2.2 代码合并

- [ ] 创建 Release PR（release → main）
- [ ] 至少1名核心开发者审查
- [ ] 确认所有检查通过
- [ ] 使用 `Squash and merge` 或 `Rebase and merge`
- [ ] **禁用** `--delete-branch` 选项

### 2.3 标签管理

- [ ] 切换到 main 分支：`git checkout main`
- [ ] 拉取最新代码：`git pull origin main`
- [ ] 创建标签：`git tag -a vX.Y.Z -m "Release vX.Y.Z"`
- [ ] 推送标签：`git push origin vX.Y.Z`

## 3. 发布后验证

### 3.1 CI/CD 流程监控

- [ ] 监控 release.yml workflow 执行状态
- [ ] 确认构建成功（绿色状态）
- [ ] 访问 GitHub Releases 页面确认包文件正常上传

### 3.2 环境同步

- [ ] 切换到 develop 分支：`git checkout develop`
- [ ] 同步 main 分支内容：`git merge main`
- [ ] 推送更新：`git push origin develop`

## 4. 紧急情况处理

### 4.1 发布回滚

**回滚条件**：生产环境严重问题、安全漏洞暴露、数据丢失风险

**回滚步骤**：
1. 创建 hotfix 分支：`git checkout -b hotfix/rollback-vX.Y.Z main`
2. 回滚代码变更
3. 创建紧急发布标签
4. 执行紧急发布流程

### 4.2 问题响应

| 问题级别 | 响应时间 |
|---------|---------|
| 严重问题 | 30分钟内响应 |
| 一般问题 | 2小时内响应 |
| 功能请求 | 24小时内评估 |

## 5. 本地预检查脚本

```bash
# 完整预检查
uv run black --check src/ tests/
uv run isort --check-only src/ tests/
uv run mypy src/ --ignore-missing-imports
uv run bandit -r src/ -s B101,B601
uv run pytest tests/unit/ --cov=src --cov-fail-under=80
```

---

**文档版本**: v0.4.1  
**最后更新**: 2026-03-30  
**关联文档**: [分支管理与发布流程规范](./分支管理与发布流程规范.md)
