# 故障排除与常见问题

本文档汇总 Nanobot Runner 开发过程中的常见问题及解决方案。

---

## 1. 环境与依赖问题

### 1.1 依赖安装失败

**问题**：`uv sync` 报错或依赖冲突

**解决方案**：
```bash
# 清理缓存并重新安装
uv cache clean
uv sync --reinstall
```

### 1.2 Windows PowerShell 激活失败

**问题**：`.venv\Scripts\activate` 无法执行

**解决方案**：
```powershell
# 设置执行策略
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser

# 然后激活
.venv\Scripts\activate
```

### 1.3 Windows 多命令链失败

**问题**：`&&` 在 PowerShell 中不工作

**解决方案**：
```powershell
# 使用 ; if($?) { } 替代 &&
uv run ruff format src/; if($?) { uv run pytest }
```

---

## 2. Polars 相关问题

### 2.1 内存溢出 (OOM)

**问题**：处理大文件时内存不足

**原因**：过早调用 `.collect()` 将 LazyFrame 转换为 DataFrame

**解决方案**：
```python
# ❌ 错误
df = pl.scan_parquet(path).collect()

# ✅ 正确：保持 LazyFrame 直到最终输出
df = pl.scan_parquet(path)
result = df.filter(...).group_by(...).agg(...)
output = result.collect()  # 仅在最终输出时 collect
```

### 2.2 Parquet 写入失败

**问题**：`Object` 类型无法写入 Parquet

**解决方案**：
```python
# 转换 Object 为 String
df = df.with_columns(
    pl.col("column_name").cast(pl.Utf8)
)
```

---

## 3. 类型检查问题

### 3.1 mypy 报错

**问题**：类型检查失败

**解决方案**：
1. 确保所有函数参数和返回值都有类型注解
2. 使用 `Optional[T]` 表示可选参数
3. 对于第三方库缺失类型存根，使用 `--ignore-missing-imports`

```bash
uv run mypy src/ --ignore-missing-imports
```

---

## 4. Agent 工具问题

### 4.1 新工具不生效

**问题**：新增的工具 LLM 无法识别

**原因**：未更新 `TOOL_DESCRIPTIONS`

**解决方案**：
```python
# src/agents/tools.py
TOOL_DESCRIPTIONS = {
    ...
    "my_new_tool": {  # ← 必须添加
        "description": "工具描述",
        "parameters": {...}
    }
}
```

### 4.2 工具返回格式错误

**问题**：工具返回的数据格式不一致

**解决方案**：统一使用标准返回格式
```python
# 成功
return {"success": True, "data": {...}}

# 失败
return {"success": False, "error": "错误信息"}
```

---

## 5. 测试问题

### 5.1 测试覆盖率不足

**问题**：覆盖率低于门禁要求

**解决方案**：
```bash
# 查看详细覆盖率报告
uv run pytest tests/unit/ --cov=src --cov-report=term-missing

# 针对性补充测试
```

### 5.2 测试数据问题

**问题**：找不到测试文件

**解决方案**：确认路径正确
```python
# 正确路径
FIXTURE_DIR = Path(__file__).parent.parent / "data" / "fixtures"
```

---

## 6. 配置问题

### 6.1 配置文件找不到

**问题**：运行时报配置文件不存在

**解决方案**：检查配置路径
```python
# 框架配置
~/.nanobot/config.json

# 业务配置
~/.nanobot-runner/config.json
```

### 6.2 飞书推送失败

**问题**：飞书消息发送失败

**解决方案**：
1. 检查 `~/.nanobot/config.json` 中的飞书配置
2. 确认 webhook_url 或 app_id/app_secret 正确
3. 检查网络连接

---

## 7. 质量门禁速查

| 检查项 | 工具 | 门禁要求 |
|--------|------|----------|
| 代码格式化 | ruff format | 零警告 |
| 代码质量 | ruff check | 零警告 |
| 类型检查 | mypy | 警告可接受 |
| 安全扫描 | bandit | 高危漏洞=0 |
| 单元测试 | pytest | 通过率100% |
| 代码覆盖率 | pytest-cov | core≥80%, agents≥70%, cli≥60% |

---

*文档版本: v1.1.0 | 更新日期: 2026-04-11*
