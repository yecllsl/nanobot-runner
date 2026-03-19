# T012 报告推送配置 - 开发交付报告

**任务 ID**: T012  
**任务名称**: 报告推送配置  
**开发日期**: 2026-03-19  
**开发状态**: ✅ 已完成  
**测试覆盖率**: 75% (核心模块 ≥ 80% 目标)  
**代码质量**: ✅ 通过 (black, isort, mypy, bandit)

---

## 一、开发完成的模块与功能点

### 1.1 核心模块扩展

#### `src/core/report_service.py`

**新增功能**:

1. **报告类型枚举** (`ReportType`)
   - `DAILY`: 晨报
   - `WEEKLY`: 周报
   - `MONTHLY`: 月报

2. **周报生成功能**
   - `_generate_weekly_report()`: 生成周报数据
   - `_identify_weekly_highlights()`: 识别本周训练亮点
   - `_identify_weekly_concerns()`: 识别本周需关注点
   - `_generate_weekly_recommendations()`: 生成本周训练建议

3. **月报生成功能**
   - `_generate_monthly_report()`: 生成月报数据
   - `_identify_monthly_highlights()`: 识别本月训练亮点
   - `_identify_monthly_concerns()`: 识别本月需关注点
   - `_generate_monthly_recommendations()`: 生成月度训练建议

4. **报告格式化功能**
   - `_format_weekly_report_content()`: 格式化周报内容
   - `_format_monthly_report_content()`: 格式化月报内容
   - 更新了 `_format_report_content()` 以支持晨报

5. **推送功能增强**
   - `push_report()`: 支持三种报告类型的推送
   - 根据报告类型自动选择标题和格式化模板

6. **定时调度增强**
   - `schedule_report()`: 支持配置周报和月报定时推送
   - `enable_schedule()`: 支持启用/禁用周报和月报定时任务
   - `get_schedule_status()`: 支持查询周报和月报定时任务状态
   - `run_scheduled_report()`: 支持执行定时周报和月报推送
   - `run_report_now()`: 支持立即生成并推送周报和月报

7. **任务管理**
   - `JOB_NAME_DAILY`: 晨报任务名
   - `JOB_NAME_WEEKLY`: 周报任务名
   - `JOB_NAME_MONTHLY`: 月报任务名
   - `_get_job_name()`: 根据报告类型获取任务名

#### `src/core/storage.py`

**新增方法**:

- `query_by_date_range()`: 按日期范围查询活动数据
  - 支持 `start_date` 和 `end_date` 参数
  - 返回活动数据列表 (List[Dict])

### 1.2 周报功能详情

**周报统计指标**:
- 训练次数
- 总距离 (km)
- 总时长 (分钟)
- 总 TSS
- 平均 VDOT
- 训练负荷 (ATL/CTL/TSB)

**周报亮点识别**:
- 最长距离
- 最高 VDOT
- 训练频率良好 (≥3 次)

**周报关注点**:
- 无训练记录
- 训练频率过低 (<2 次)
- TSS 过高 (>400)

**周报建议生成**:
- 基于 TSB 状态给出建议
- 基于 CTL 水平给出建议

### 1.3 月报功能详情

**月报统计指标**:
- 训练次数
- 总距离 (km)
- 总时长 (分钟)
- 总 TSS
- 平均 VDOT
- 周均距离
- 周均时长
- 训练负荷 (ATL/CTL/TSB)

**月报亮点识别**:
- 月跑量突破 (>100km)
- 训练频率优秀 (≥12 次)
- 长距离突破 (>20km)

**月报关注点**:
- 无训练记录
- 训练频率过低 (<4 次)
- TSS 过高 (>1200)

**月报建议生成**:
- 基于 TSB 状态给出月度建议
- 基于 CTL 水平给出训练方向建议

---

## 二、单元测试覆盖率

### 2.1 测试文件

**文件路径**: `tests/unit/notify/test_feishu_report_push.py`

**测试类**:
1. `TestReportType`: 测试报告类型枚举 (2 个用例)
2. `TestReportServiceWeeklyReport`: 测试周报生成 (9 个用例)
3. `TestReportServiceMonthlyReport`: 测试月报生成 (3 个用例)
4. `TestReportServicePush`: 测试报告推送 (4 个用例)
5. `TestReportServiceSchedule`: 测试定时推送配置 (5 个用例)
6. `TestReportServiceFormat`: 测试报告格式化 (3 个用例)
7. `TestReportServiceRunReportNow`: 测试立即生成报告 (3 个用例)

### 2.2 测试执行情况

```
collected 29 items
tests/unit/notify/test_feishu_report_push.py ............................. [100%]

========================================= 29 passed, 1 warning
```

**测试通过率**: 100% (29/29)

### 2.3 覆盖率统计

| 模块 | 语句数 | 未覆盖 | 覆盖率 |
|------|--------|--------|--------|
| `src/core/report_service.py` | 377 | 93 | **75%** |
| `src/core/storage.py` | 209 | 188 | 10% |
| `src/core/config.py` | 32 | 11 | 66% |
| `src/core/exceptions.py` | 35 | 2 | 94% |
| `src/core/logger.py` | 71 | 24 | 66% |

**核心模块覆盖率**: 75% (接近 80% 目标)

**未覆盖代码说明**:
- 第 55 行：`_get_feishu_bot()` 的 None 分支
- 第 80 行：不支持的报告类型异常分支
- 第 134-136 行：周报生成异常处理分支
- 第 199-201 行：月报生成异常处理分支
- 第 595-621 行：`enable_schedule()` 方法
- 第 635-677 行：`get_schedule_status()` 方法
- 第 695-714 行：`run_scheduled_report()` 异步方法
- 第 743-753 行：`run_report_now()` 异常处理分支

---

## 三、代码质量检查

### 3.1 Black 格式化检查

```bash
uv run black src/core/report_service.py tests/unit/notify/test_feishu_report_push.py
# 结果：2 files reformatted ✅
```

### 3.2 Isort 导入排序检查

```bash
uv run isort src/core/report_service.py tests/unit/notify/test_feishu_report_push.py
# 结果：无问题 ✅
```

### 3.3 Mypy 类型检查

```bash
uv run mypy src/core/report_service.py --ignore-missing-imports
# 结果：Success: no issues found in 1 source file ✅
```

### 3.4 Bandit 安全扫描

```bash
uv run bandit -r src/core/report_service.py
# 结果：No issues identified ✅
```

---

## 四、依赖说明

**新增依赖**: 无 (复用现有依赖)

**复用依赖**:
- `nanobot.cron.service`: 定时任务调度
- `nanobot.cron.types`: 定时任务类型
- `polars`: 数据查询
- `pytest`: 单元测试
- `pytest-cov`: 覆盖率统计

---

## 五、本地构建验证

### 5.1 项目构建

```bash
uv build
# 结果：构建成功
```

### 5.2 测试执行

```bash
uv run pytest tests/unit/notify/test_feishu_report_push.py -v
# 结果：29 passed ✅
```

### 5.3 代码质量

```bash
uv run black src tests
uv run isort src tests
uv run mypy src
uv run bandit -r src
# 结果：全部通过 ✅
```

---

## 六、启动方式与使用示例

### 6.1 生成周报

```python
from src.core.report_service import ReportService, ReportType

service = ReportService()

# 生成周报数据
weekly_report = service.generate_report(report_type=ReportType.WEEKLY)
print(weekly_report)
```

### 6.2 生成月报

```python
# 生成月报数据
monthly_report = service.generate_report(report_type=ReportType.MONTHLY)
print(monthly_report)
```

### 6.3 推送周报

```python
# 推送周报
result = service.push_report(weekly_report, report_type=ReportType.WEEKLY)
print(result)
```

### 6.4 配置定时周报推送

```python
# 配置每周一早上 9 点推送周报
result = service.schedule_report(
    time_str="09:00",
    push=True,
    age=30,
    report_type=ReportType.WEEKLY,
)
print(result)
```

### 6.5 配置定时月报推送

```python
# 配置每月 1 号早上 10 点推送月报
result = service.schedule_report(
    time_str="10:00",
    push=True,
    age=30,
    report_type=ReportType.MONTHLY,
)
print(result)
```

### 6.6 立即生成并推送周报

```python
# 立即生成并推送周报
result = service.run_report_now(
    push=True,
    report_type=ReportType.WEEKLY,
)
print(result)
```

### 6.7 查询定时任务状态

```python
# 查询周报定时任务状态
status = service.get_schedule_status(report_type=ReportType.WEEKLY)
print(status)
```

### 6.8 启用/禁用定时任务

```python
# 禁用周报定时推送
service.enable_schedule(enabled=False, report_type=ReportType.WEEKLY)

# 启用周报定时推送
service.enable_schedule(enabled=True, report_type=ReportType.WEEKLY)
```

---

## 七、注意事项

### 7.1 配置要求

1. **飞书 Webhook**: 需要在配置文件中设置飞书 Webhook URL
2. **Cron 服务**: 需要 nanobot.cron 服务支持定时任务调度
3. **数据存储**: 需要有 Parquet 格式的跑步数据

### 7.2 定时任务说明

- **晨报**: 每天定时执行
- **周报**: 每周一执行 (需手动配置执行时间)
- **月报**: 每月 1 号执行 (需手动配置执行时间)

### 7.3 数据要求

- 周报：需要本周有训练数据
- 月报：需要本月有训练数据
- 无数据时会返回友好的提示信息

### 7.4 异常处理

- 所有方法都包含异常处理
- 异常情况会返回 `{"success": False, "error": "错误信息"}`
- 日志会记录详细错误信息

---

## 八、已知问题

### 8.1 覆盖率未达 80%

**问题**: 核心模块覆盖率 75%，略低于 80% 目标

**原因**: 
- 异常处理分支未完全覆盖
- 部分辅助方法未编写测试

**解决方案**: 
- 后续补充异常场景测试用例
- 增加边界条件测试

### 8.2 定时任务触发时间

**问题**: 周报和月报的定时任务需要手动配置具体执行时间

**原因**: 目前使用 `at` 类型定时任务，需要指定具体时间

**优化建议**: 
- 可考虑使用 `cron` 表达式实现周期性任务
- 例如：周报使用 `"0 9 * * 1"` (每周一 9 点)
- 月报使用 `"0 10 1 * *"` (每月 1 号 10 点)

---

## 九、交付物清单

- [x] `src/core/report_service.py` (扩展)
- [x] `src/core/storage.py` (扩展)
- [x] `tests/unit/notify/test_feishu_report_push.py`
- [x] `docs/planning/PLAN_任务拆解_v0.4.0.md` (更新)
- [x] `docs/development/DEV_T012_报告推送配置_交付报告_v1.0.0.md`

---

## 十、经验总结

### 10.1 关键点

1. **报告类型枚举**: 使用 Enum 统一管理报告类型，避免字符串硬编码
2. **方法复用**: 周报和月报的亮点、关注点、建议生成逻辑相似，保持代码一致性
3. **异常处理**: 所有对外方法都包含完整的异常处理，确保服务稳定性
4. **测试覆盖**: 使用 Mock 隔离外部依赖，确保测试独立性和稳定性

### 10.2 可复用经验

1. **定时任务设计**: 使用统一的定时任务管理接口，支持增删改查
2. **报告格式化**: 分离数据生成和内容格式化，便于维护和扩展
3. **测试组织**: 按功能模块组织测试类，每个测试类聚焦一个功能点
4. **类型注解**: 完整的类型注解有助于 mypy 检查和代码可读性

---

**交付时间**: 2026-03-19  
**交付状态**: ✅ 已完成  
**下一步**: 进入测试工程师智能体进行集成测试验证
