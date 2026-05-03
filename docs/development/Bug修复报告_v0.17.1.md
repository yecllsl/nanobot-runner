# Bug修复报告 - Nanobot Runner v0.17.1

> **报告版本**: v1.0
> **修复日期**: 2026-05-03
> **修复版本**: v0.17.1 (hotfix-0.17.1)
> **修复人员**: 开发工程师智能体

---

## 1. 修复概述

### 1.1 修复Bug列表

| Bug ID | 所属模块 | 严重等级 | Bug标题 | 修复状态 |
|--------|---------|---------|---------|---------|
| BUG-UAT-001 | 系统管理 | 一般 | `system init --force` 升级迁移失败 | ✅ 已修复 |
| BUG-UAT-002 | 偏好管理 | 一般 | 保存profile.json失败 | ✅ 已修复 |

### 1.2 修复统计

| 严重等级 | 修复数 | 占比 |
|---------|--------|------|
| 致命 | 0 | 0% |
| 严重 | 0 | 0% |
| 一般 | 2 | 100% |
| 优化 | 0 | 0% |
| **合计** | **2** | **100%** |

---

## 2. BUG-UAT-001 修复详情

### 2.1 Bug描述

**标题**: `system init --force` 升级迁移失败

**现象**: 执行 `system init --force` 时，如果检测到旧版本（非0.9.4），会进入MIGRATE模式，但迁移失败提示"nanobot配置文件不存在或无法读取"。

### 2.2 根因分析

1. `system init` 命令通过 `MigrationEngine.detect_old_version()` 检测旧版本
2. 当当前配置版本号不是0.9.4时，会被判定为需要迁移的旧版本
3. 进入MIGRATE模式后，调用 `ConfigMigrator.migrate_from_nanobot()`
4. `migrate_from_nanobot()` 只尝试从 `~/.nanobot/config.json` 加载配置进行迁移
5. 在UAT环境中，`~/.nanobot/config.json` 不存在，导致迁移失败

**核心问题**: MIGRATE模式假设nanobot配置文件一定存在，没有处理nanobot配置不存在但当前配置已存在的情况。

### 2.3 修复方案

**修改文件**: `src/core/init/wizard.py`

**修改内容**: 在 `_run_migrate_mode` 方法中，当迁移失败且错误原因是"nanobot配置文件不存在"时，如果用户使用了 `--force` 参数，则回退到FRESH模式重新初始化。

```python
# 在 _run_migrate_mode 方法中
if not result.success:
    # 如果迁移失败是因为nanobot配置文件不存在，且用户使用了--force
    # 则回退到FRESH模式重新初始化
    if any("nanobot配置文件不存在" in err for err in result.errors) and force:
        logger.warning("nanobot配置不存在，回退到全新初始化模式")
        return self.run(
            mode=InitMode.FRESH,
            force=force,
            skip_optional=True,
            workspace_dir=target_dir,
            agent_mode=False,
        )
    return InitResult(
        success=False,
        errors=result.errors,
        warnings=result.warnings,
    )
```

### 2.4 修复验证

**验证命令**:
```bash
$env:NANOBOT_CONFIG_DIR="$PWD\.nanobot-runner-uat"
uv run nanobotrun system init --force
```

**验证结果**:
- 退出码: 0
- 输出: "✓ 初始化完成！"
- 日志: "nanobot配置不存在，回退到全新初始化模式"
- 状态: ✅ 修复成功

---

## 3. BUG-UAT-002 修复详情

### 3.1 Bug描述

**标题**: 保存profile.json失败

**现象**: 执行 `preference set` 或 `preference reset` 时，虽然输出"偏好已更新"，但日志显示ERROR: `保存 profile.json 失败：'dict' object has no attribute 'to_dict'`

### 3.2 根因分析

1. `preference.py` 中的 `set_preference` 和 `reset_preferences` 函数将偏好数据保存到profile.json
2. 代码逻辑：先加载现有profile，更新preferences字段，然后调用 `profile_storage.save_profile_json(profile_dict)`
3. 但 `profile_dict` 是一个普通Python字典（通过 `profile.to_dict()` 或直接 `{}` 获得）
4. `ProfileStorageManager.save_profile_json()` 方法期望接收 `RunnerProfile` 对象，直接调用 `profile.to_dict()`
5. 当传入dict时，`dict.to_dict()` 不存在，导致AttributeError

**核心问题**: `save_profile_json` 方法类型注解声明接收 `RunnerProfile` 对象，但实际调用时传入的是dict。

### 3.3 修复方案

**修改文件**: `src/core/base/profile.py`

**修改内容**: 修改 `save_profile_json` 方法，支持同时接收 `RunnerProfile` 对象和 `dict` 两种类型。

```python
def save_profile_json(self, profile: RunnerProfile | dict[str, Any]) -> bool:
    """保存画像到 profile.json

    Args:
        profile: RunnerProfile 对象或字典

    Returns:
        bool: 保存是否成功
    """
    try:
        if isinstance(profile, dict):
            profile_data = profile.copy()
            user_id = profile_data.get("user_id", "default_user")
        else:
            profile_data = profile.to_dict()
            user_id = profile.user_id

        profile_data["updated_at"] = datetime.now().isoformat()

        with open(self.profile_json_path, "w", encoding="utf-8") as f:
            json.dump(profile_data, f, indent=2, ensure_ascii=False)

        logger.info(f"画像已保存到 profile.json: {user_id}")
        return True
    except Exception as e:
        logger.error(f"保存 profile.json 失败：{e}")
        raise RuntimeError(f"保存 profile.json 失败：{e}") from e
```

### 3.4 修复验证

**验证命令**:
```bash
$env:NANOBOT_CONFIG_DIR="$PWD\.nanobot-runner-uat"
uv run nanobotrun preference set training_time evening
uv run nanobotrun preference reset
```

**验证结果**:
- `preference set`: 退出码0，输出"偏好已更新: training_time = evening"，无ERROR日志
- `preference reset`: 退出码0，输出"偏好已重置为默认值"，无ERROR日志
- 状态: ✅ 修复成功

---

## 4. 回归测试

### 4.1 单元测试

**测试命令**: `uv run pytest tests/unit/ -q`

**测试结果**:
- 通过: 2846
- 失败: 1（`test_consecutive_backup_different_versions`，与本次修复无关的memory模块测试）
- 跳过: 1
- 警告: 4
- 覆盖率: 81%

**结论**: 无新增测试失败，修复未引入回归问题。

### 4.2 UAT回归验证

| 验证项 | 命令 | 结果 |
|--------|------|------|
| system init --force | `uv run nanobotrun system init --force` | ✅ 通过 |
| preference set | `uv run nanobotrun preference set training_time evening` | ✅ 通过 |
| preference reset | `uv run nanobotrun preference reset` | ✅ 通过 |

---

## 5. 代码变更清单

| 文件路径 | 变更类型 | 变更说明 |
|---------|---------|---------|
| `src/core/init/wizard.py` | 修改 | 在 `_run_migrate_mode` 中增加nanobot配置不存在时的回退逻辑 |
| `src/core/base/profile.py` | 修改 | `save_profile_json` 方法支持接收dict类型参数 |

---

## 6. 修复总结

### 6.1 修复效果

| Bug ID | 修复前 | 修复后 |
|--------|--------|--------|
| BUG-UAT-001 | `system init --force` 失败，退出码1 | `system init --force` 成功，退出码0 |
| BUG-UAT-002 | `preference set` 有ERROR日志，保存失败 | `preference set` 无ERROR日志，保存成功 |

### 6.2 风险评估

| 风险项 | 风险等级 | 说明 |
|--------|---------|------|
| 回退逻辑影响正常迁移 | 低 | 仅在nanobot配置不存在且使用--force时触发，不影响正常迁移流程 |
| dict类型支持影响现有功能 | 低 | 新增类型支持，不影响原有RunnerProfile对象的保存逻辑 |

### 6.3 后续建议

1. 建议执行完整UAT回归测试，确保修复不影响其他功能
2. 建议在后续版本中为 `ProfileStorageManager.save_profile_json` 添加单元测试，覆盖dict和RunnerProfile两种输入类型
3. 建议优化 `detect_old_version` 逻辑，更准确地判断是否需要迁移

---

**报告生成时间**: 2026-05-03 14:05
**报告版本**: v1.0
