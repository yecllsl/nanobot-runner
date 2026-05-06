# UAT 数据导出测试用例（UAT-066 ~ UAT-070）

> **返回精简版指南**: [../用户验收测试指南.md](../用户验收测试指南.md)

---

## UAT-066: CSV导出

| 项目 | 内容 |
|------|------|
| **测试目的** | 验证跑步数据导出为CSV格式功能 |
| **前置条件** | 已初始化环境，已导入跑步数据（至少包含10条记录） |
| **执行命令** | `uv run nanobotrun export sessions --format csv` |
| **预期结果** | 退出码为0，生成CSV文件，文件内容包含跑步数据字段 |
| **优先级** | P0 |

**自动化判定规则**:
```json
{
  "pass_condition": "exit_code == 0 AND file exists with .csv extension AND file size > 0",
  "fail_condition": "exit_code != 0 OR stdout contains '错误:' OR file is empty"
}
```

**人工验收要点**:
- [ ] CSV文件正常生成
- [ ] 文件包含表头行（字段名）
- [ ] 数据行与数据库记录数量一致
- [ ] 字段分隔符正确（逗号）
- [ ] 特殊字符（如中文）编码正确（UTF-8）
- [ ] 可用Excel或其他CSV阅读器正常打开

**结果记录**:
- [ ] 通过 / [ ] 失败
- 导出文件路径: _____
- 文件大小: _____KB
- 数据行数: _____
- 导出耗时: _____秒
- 异常信息（如失败）: _____

---

## UAT-067: JSON导出

| 项目 | 内容 |
|------|------|
| **测试目的** | 验证跑步数据导出为JSON格式功能 |
| **前置条件** | UAT-066前置条件满足 |
| **执行命令** | `uv run nanobotrun export sessions --format json` |
| **预期结果** | 退出码为0，生成JSON文件，文件格式合法，包含跑步数据 |
| **优先级** | P0 |

**自动化判定规则**:
```json
{
  "pass_condition": "exit_code == 0 AND file exists with .json extension AND file size > 0 AND valid JSON format",
  "fail_condition": "exit_code != 0 OR stdout contains '错误:' OR file is empty OR invalid JSON"
}
```

**人工验收要点**:
- [ ] JSON文件正常生成
- [ ] JSON格式合法（可用json.loads()解析）
- [ ] 数据结构为数组，每个元素为一条跑步记录
- [ ] 字段名清晰，数据类型正确
- [ ] 嵌套结构（如有）格式正确

**结果记录**:
- [ ] 通过 / [ ] 失败
- 导出文件路径: _____
- 文件大小: _____KB
- 记录数: _____
- JSON格式验证: [ ] 合法 / [ ] 非法
- 异常信息（如失败）: _____

---

## UAT-068: Parquet导出

| 项目 | 内容 |
|------|------|
| **测试目的** | 验证跑步数据导出为Parquet格式功能 |
| **前置条件** | UAT-066前置条件满足 |
| **执行命令** | `uv run nanobotrun export sessions --format parquet` |
| **预期结果** | 退出码为0，生成Parquet文件，文件可用Polars/PyArrow读取 |
| **优先级** | P0 |

**自动化判定规则**:
```json
{
  "pass_condition": "exit_code == 0 AND file exists with .parquet extension AND file size > 0",
  "fail_condition": "exit_code != 0 OR stdout contains '错误:' OR file is empty"
}
```

**人工验收要点**:
- [ ] Parquet文件正常生成
- [ ] 文件可用Polars读取：`pl.read_parquet("export.parquet")`
- [ ] 数据行数与源数据一致
- [ ] 字段类型正确（日期、数值、字符串等）
- [ ] 文件大小合理（Parquet压缩效率高）

**验证脚本**:
```python
import polars as pl
df = pl.read_parquet("导出的文件路径.parquet")
print(f"行数: {len(df)}, 列数: {len(df.columns)}")
print(df.head())
```

**结果记录**:
- [ ] 通过 / [ ] 失败
- 导出文件路径: _____
- 文件大小: _____KB
- 行数: _____
- 列数: _____
- 验证脚本执行: [ ] 成功 / [ ] 失败
- 异常信息（如失败）: _____

---

## UAT-069: 日期范围筛选导出

| 项目 | 内容 |
|------|------|
| **测试目的** | 验证按日期范围筛选导出数据功能 |
| **前置条件** | 已导入覆盖多个日期的跑步数据 |
| **执行命令** | `uv run nanobotrun export sessions --format csv --start 2024-01-01 --end 2024-12-31` |
| **预期结果** | 退出码为0，仅导出指定日期范围内的数据 |
| **优先级** | P0 |

**自动化判定规则**:
```json
{
  "pass_condition": "exit_code == 0 AND file exists AND all records date within [start, end] range",
  "fail_condition": "exit_code != 0 OR stdout contains '错误:' OR records outside date range"
}
```

**人工验收要点**:
- [ ] 导出文件仅包含指定日期范围内的数据
- [ ] 无日期范围外的数据混入
- [ ] 日期边界值处理正确（包含start和end当天）
- [ ] 数据按日期排序（可选）
- [ ] 导出统计信息显示正确

**验证脚本**:
```python
import csv
from datetime import datetime

start_date = datetime(2024, 1, 1)
end_date = datetime(2024, 12, 31)

with open("导出的文件路径.csv", "r", encoding="utf-8") as f:
    reader = csv.DictReader(f)
    for row in reader:
        date = datetime.strptime(row["date"], "%Y-%m-%d")
        assert start_date <= date <= end_date, f"日期 {date} 超出范围"
print("所有日期均在范围内")
```

**结果记录**:
- [ ] 通过 / [ ] 失败
- 指定日期范围: _____ 至 _____
- 导出数据行数: _____
- 日期范围外数据: _____条（应为0）
- 异常信息（如失败）: _____

---

## UAT-070: 导出到指定路径

| 项目 | 内容 |
|------|------|
| **测试目的** | 验证导出数据到指定路径功能 |
| **前置条件** | UAT-066前置条件满足 |
| **执行命令** | `uv run nanobotrun export sessions --format csv --output ./exports/my_runs.csv` |
| **预期结果** | 退出码为0，文件生成到指定路径，目录不存在时自动创建 |
| **优先级** | P1 |

**自动化判定规则**:
```json
{
  "pass_condition": "exit_code == 0 AND file exists at specified path AND file size > 0",
  "fail_condition": "exit_code != 0 OR stdout contains '错误:' OR file not at specified path"
}
```

**人工验收要点**:
- [ ] 文件生成到指定路径
- [ ] 目录不存在时自动创建（如./exports/）
- [ ] 文件内容完整，与默认路径导出一致
- [ ] 路径支持相对路径和绝对路径
- [ ] 路径包含中文时正常处理

**结果记录**:
- [ ] 通过 / [ ] 失败
- 指定路径: _____
- 文件是否生成: [ ] 是 / [ ] 否
- 目录自动创建: [ ] 是 / [ ] 否 / [ ] 不适用
- 异常信息（如失败）: _____

---

## 测试环境要求

| 要求 | 说明 |
|------|------|
| **Python版本** | 3.11+ |
| **依赖包** | pyarrow（Parquet支持）、polars（数据处理） |
| **测试数据** | 至少包含10条跑步记录，覆盖多个日期 |
| **磁盘空间** | 至少10MB可用空间（用于导出文件） |
| **文件权限** | 当前用户对导出目录有写入权限 |

## 导出格式对比

| 格式 | 优点 | 缺点 | 适用场景 |
|------|------|------|---------|
| **CSV** | 通用性强，可用Excel打开 | 无类型信息，文件较大 | 数据交换、简单分析 |
| **JSON** | 支持嵌套结构，Web友好 | 文件较大，解析较慢 | API集成、Web应用 |
| **Parquet** | 压缩率高，类型保留，查询快 | 需专用工具读取 | 大数据分析、长期存储 |

## 常见问题

| 问题 | 原因 | 解决方案 |
|------|------|---------|
| 导出文件为空 | 日期范围内无数据 | 检查日期范围，调整--start和--end |
| CSV乱码 | 编码问题 | 使用UTF-8编码打开，或指定--encoding参数 |
| JSON格式错误 | 数据包含特殊字符 | 检查数据，确保转义正确 |
| Parquet读取失败 | pyarrow未安装 | 运行 `uv sync` 安装依赖 |
| 权限错误 | 无写入权限 | 检查目录权限，使用有权限的路径 |
| 导出速度慢 | 数据量大 | 使用日期范围筛选，分批导出 |
