# Bug修复报告 - v0.18.1 hotfix

> **版本**: v0.18.1 | **修复日期**: 2026-05-05 | **来源**: UAT测试执行报告

---

## 1. 修复概览

| Bug ID | 严重等级 | 描述 | 状态 |
|--------|----------|------|------|
| BUG-001 | 严重 | 周报告生成失败 - 'VdotTrendItem' object has no attribute 'get' | ✅ 已修复 |
| BUG-002 | 一般 | VDOT趋势图数据点重复显示 | ✅ 已修复 |
| BUG-003 | 一般 | PowerShell输出中文显示为乱码 | ✅ 已修复 |
| BUG-004 | 一般 | 可视化命令不支持--output导出选项 | ✅ 已修复 |
| BUG-005 | 优化 | 月度报告不支持导出 | ✅ 已修复 |

---

## 2. 修复详情

### BUG-001: 周报告生成失败

**根因**: `_format_vdot_trend` 方法使用 `item.get()` 访问 VDOT 趋势数据，但 `VdotTrendItem` 是 dataclass 对象而非字典，不支持 `.get()` 方法。

**修复方案**: 修改 `_format_vdot_trend` 方法，使用 `isinstance` 判断数据类型，对 `VdotTrendItem` 对象使用属性访问，对 `dict` 使用 `.get()` 方法。

**修改文件**: `src/core/report/generator.py`

**关键变更**:
```python
def _format_vdot_trend(self, vdot_trend: list[VdotTrendItem | dict[str, Any]]) -> str:
    for item in vdot_trend[-7:]:
        if isinstance(item, VdotTrendItem):
            date = item.date
            vdot = item.vdot
            distance = item.distance / 1000
        else:
            date = item.get("date", "")
            vdot = item.get("vdot", 0.0)
            distance = item.get("distance", 0.0) / 1000
```

**回归测试**: 新增 2 个测试用例验证 VdotTrendItem 对象和混合类型输入

---

### BUG-002: VDOT趋势图数据点重复显示

**根因**: `_convert_vdot_to_chart_data` 方法未对同一天的多条记录进行聚合，导致同一日期出现多个数据点。

**修复方案**: 使用 `defaultdict` 按日期聚合 VDOT 值，同一天多条记录取平均值。

**修改文件**: `src/cli/handlers/viz_handler.py`

**关键变更**:
```python
daily_vdot: dict[str, list[float]] = defaultdict(list)
for item in trend_data:
    daily_vdot[item.date].append(item.vdot)

labels = sorted(daily_vdot.keys())
values = [sum(daily_vdot[d]) / len(daily_vdot[d]) for d in labels]
```

**回归测试**: 新增 4 个测试用例验证单日单条、同日多条聚合、空数据、日期排序

---

### BUG-003: PowerShell输出中文显示为乱码

**根因**: Windows PowerShell 默认编码非 UTF-8，导致中文字符无法正确显示。

**修复方案**: 在 `PlotextRenderer` 的所有渲染方法中调用 `_ensure_utf8_output()` 函数，在 Windows 平台上将 `sys.stdout` 重新配置为 UTF-8 编码。

**修改文件**: `src/core/visualization/plotext_renderer.py`

**关键变更**:
```python
def _ensure_utf8_output() -> None:
    if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except (OSError, ValueError):
            pass
```

**回归测试**: 新增 3 个测试用例验证函数调用安全、Windows 平台行为、非 Windows 平台行为

---

### BUG-004: 可视化命令不支持--output导出选项

**根因**: `viz vdot`、`viz load`、`viz hr-zones` 命令未提供 `--output` 参数，用户无法将图表导出到文件。

**修复方案**: 为所有可视化命令添加 `--output` / `-o` 可选参数，支持将图表文本内容导出到指定文件。

**修改文件**: `src/cli/commands/viz.py`

**关键变更**:
```python
output: Path | None = typer.Option(
    None, "--output", "-o", help="导出图表到文件（纯文本）"
)
# ...
if output:
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(result, encoding="utf-8")
```

---

### BUG-005: 月度报告不支持导出

**根因**: 月度报告的 `--output` 参数已存在，但报告生成因 BUG-001 失败导致导出功能不可用。BUG-001 修复后此问题同步解决。

**修改文件**: 无需额外修改

---

## 3. 测试验证

### 单元测试结果

| 测试文件 | 用例数 | 通过 | 失败 | 跳过 |
|----------|--------|------|------|------|
| tests/unit/core/report/test_generator.py | 8 (FormatMethods) | 8 | 0 | 0 |
| tests/unit/cli/handlers/test_viz_handler.py | 9 | 9 | 0 | 0 |
| tests/unit/core/visualization/test_plotext_renderer.py | 3 (UTF8) | 3 | 0 | 0 |
| **全量单元测试** | **2985** | **2985** | **0** | **1** |

### 新增测试用例

| Bug ID | 新增测试 | 文件 |
|--------|----------|------|
| BUG-001 | `test_format_vdot_trend_with_vdot_trend_item`, `test_format_vdot_trend_mixed_types` | test_generator.py |
| BUG-002 | `test_single_item_per_day`, `test_duplicate_dates_aggregated`, `test_empty_trend_data`, `test_sorted_labels` | test_viz_handler.py |
| BUG-003 | `test_ensure_utf8_output_no_exception`, `test_ensure_utf8_output_windows`, `test_ensure_utf8_output_non_windows` | test_plotext_renderer.py |

### 覆盖率

- 全量单元测试覆盖率: **80%**
- 修复模块覆盖率: generator 91%, viz_handler 69%, plotext_renderer 91%

---

## 4. 修改文件清单

| 文件路径 | 修改类型 | 关联Bug |
|----------|----------|---------|
| src/core/report/generator.py | 修改 | BUG-001 |
| src/cli/handlers/viz_handler.py | 修改 | BUG-002 |
| src/core/visualization/plotext_renderer.py | 修改 | BUG-003 |
| src/cli/commands/viz.py | 修改 | BUG-004 |
| tests/unit/core/report/test_generator.py | 修改 | BUG-001 |
| tests/unit/cli/handlers/test_viz_handler.py | 新增 | BUG-002 |
| tests/unit/core/visualization/test_plotext_renderer.py | 修改 | BUG-003 |

---

## 5. 已知问题与注意事项

1. `_ensure_utf8_output()` 仅在图表渲染时生效，其他 CLI 输出的中文编码问题可能仍需在更上层统一处理
2. 可视化导出为纯文本格式，后续可考虑支持 SVG/PNG 等图形格式
3. VDOT 趋势同日聚合取平均值，未来可考虑提供聚合策略选项（最大值/最近值等）
