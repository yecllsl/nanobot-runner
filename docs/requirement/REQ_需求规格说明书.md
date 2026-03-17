# 技术规格说明书

**版本**: v0.3.0  
**最后更新**: 2026-03-17  
**目标读者**: 开发工程师、测试工程师、架构师

---

## 1. 引言

### 1.1 文档目的

本文档详细规定 Nanobot Runner 系统需要实现的具体功能、性能指标、接口要求及验收标准，为开发团队提供明确的技术实现指导。

### 1.2 项目概述

Nanobot Runner 是一款基于 nanobot-ai 底座的本地化 AI 跑步助理，通过 Parquet 列式存储与 Polars 高性能计算引擎，为技术型跑者提供企业级 BI 能力。

**参考文档**:
- [用户需求文档](./REQ_用户需求文档.md) - 业务目标与使用场景
- [架构设计文档](../architecture/ARC_架构设计.md) - 系统架构设计

---

## 2. 功能需求规格

### 2.1 数据导入与管理模块

#### FR-001 FIT 文件解析

| 属性 | 描述 |
|------|------|
| **需求编号** | FR-001 |
| **需求名称** | FIT 文件解析 |
| **优先级** | P0 |
| **功能描述** | 底层解析 `.fit` 格式，提取心率、步频、功率、轨迹等元数据 |
| **输入** | `.fit` 文件路径 |
| **输出** | 结构化数据（DataFrame） |
| **验收标准** | 1. 成功解析 Garmin 标准格式<br>2. 错误捕获率 100%<br>3. 异常数据标记清晰 |
| **技术实现** | 使用 `fitparse` 库进行底层解析 |

#### FR-002 高效存储与去重

| 属性 | 描述 |
|------|------|
| **需求编号** | FR-002 |
| **需求名称** | 高效存储与去重 |
| **优先级** | P0 |
| **存储格式** | Apache Parquet 列式存储，按年份分片 |
| **去重机制** | 基于 `SHA256(activity_id + timestamp + distance)` 生成指纹 |
| **验收标准** | 1. 导入流程支持断点续传<br>2. 重复导入数据记录零增长 |
| **技术实现** | 使用 `pyarrow` + `polars` 实现存储与查询 |

### 2.2 CLI 交互模块

#### FR-003 命令行接口

| 属性 | 描述 |
|------|------|
| **需求编号** | FR-003 |
| **需求名称** | 命令行接口 |
| **优先级** | P0 |
| **命令列表** | `nanobotrun import <path>` - 触发解析与存储<br>`nanobotrun stats [--year YYYY]` - 查询统计数据<br>`nanobotrun chat` - 启动 Agent 交互模式 |
| **验收标准** | CLI 启动速度 < 1s |

#### FR-004 Agent 工具接口

| 属性 | 描述 |
|------|------|
| **需求编号** | FR-004 |
| **需求名称** | Agent 工具接口 |
| **优先级** | P0 |
| **工具列表** | `get_running_stats` - 获取跑步统计<br>`get_recent_runs` - 获取最近记录<br>`calculate_vdot_for_run` - 计算 VDOT<br>`get_vdot_trend` - 获取 VDOT 趋势<br>`get_hr_drift_analysis` - 心率漂移分析<br>`get_training_load` - 训练负荷计算<br>`query_by_date_range` - 按日期范围查询<br>`query_by_distance` - 按距离查询 |
| **接口格式** | OpenAI Function Calling 格式 |

### 2.3 数据分析引擎模块

#### FR-005 体能指标计算

| 属性 | 描述 |
|------|------|
| **需求编号** | FR-005 |
| **需求名称** | 体能指标计算 |
| **优先级** | P0 |
| **指标列表** | TSS (Training Stress Score) - 训练压力分数<br>ATL (Acute Training Load) - 急性训练负荷<br>CTL (Chronic Training Load) - 慢性训练负荷<br>TSB (Training Stress Balance) - 训练压力平衡 |
| **计算公式** | TSS = duration × IF² × 100<br>ATL = 昨日ATL × 0.7 + 今日TSS × 0.3<br>CTL = 昨日CTL × 0.9 + 今日TSS × 0.1<br>TSB = CTL - ATL |
| **验收标准** | 计算精度误差 < 1% |

#### FR-006 VDOT 跑力值计算

| 属性 | 描述 |
|------|------|
| **需求编号** | FR-006 |
| **需求名称** | VDOT 跑力值计算 |
| **优先级** | P0 |
| **计算公式** | 基于 Jack Daniels' VDOT 公式（距离 ≥ 1500m） |
| **验收标准** | 与标准 VDOT 表对比误差 < 2% |

#### FR-007 心率漂移分析

| 属性 | 描述 |
|------|------|
| **需求编号** | FR-007 |
| **需求名称** | 心率漂移分析 |
| **优先级** | P1 |
| **算法** | 计算前 50% 和后 50% 配速的心率相关性，相关性 < -0.7 判定为漂移 |
| **输出** | 漂移率百分比、有氧能力评估 |

### 2.4 飞书推送模块

#### FR-008 飞书消息推送

| 属性 | 描述 |
|------|------|
| **需求编号** | FR-008 |
| **需求名称** | 飞书消息推送 |
| **优先级** | P1 |
| **推送类型** | 导入完成通知、每日晨报、周报/月报 |
| **接口** | Webhook URL 配置 |
| **消息格式** | Markdown / 富文本卡片 |

---

## 3. 非功能性需求

### 3.1 性能需求

| 需求编号 | 需求描述 | 目标值 |
|---------|---------|--------|
| NFR-001 | 数据导入性能 | 单文件 < 2s，批量 100 文件 < 30s |
| NFR-002 | 查询响应时间 | 百万级数据聚合查询 < 3s |
| NFR-003 | 内存占用 | 处理 10,000 条记录峰值内存 < 500MB |

### 3.2 可靠性需求

| 需求编号 | 需求描述 | 目标值 |
|---------|---------|--------|
| NFR-004 | 数据完整性 | 导入过程异常中断可恢复 |
| NFR-005 | 错误处理 | 所有异常场景有明确错误码和日志 |

### 3.3 安全性需求

| 需求编号 | 需求描述 | 实现方式 |
|---------|---------|----------|
| NFR-006 | 数据隐私 | 本地存储，零外联设计 |
| NFR-007 | 敏感信息 | 配置文件加密存储 Webhook URL |

### 3.4 兼容性需求

| 需求编号 | 需求描述 | 支持范围 |
|---------|---------|----------|
| NFR-008 | 操作系统 | Windows 10+, macOS 12+, Ubuntu 20.04+ |
| NFR-009 | Python 版本 | 3.11, 3.12 |
| NFR-010 | 设备格式 | Garmin, Wahoo 标准 FIT 文件 |

---

## 4. 数据模型

### 4.1 核心数据表

```python
# 活动记录表 (activities_{year}.parquet)
{
    "activity_id": pl.Utf8,        # 活动唯一标识
    "timestamp": pl.Datetime,       # 活动时间戳
    "source_file": pl.Utf8,        # 源文件路径
    "filename": pl.Utf8,           # 文件名
    "total_distance": pl.Float64,  # 总距离（米）
    "total_timer_time": pl.Float64, # 总时间（秒）
    "avg_heart_rate": pl.Float64,  # 平均心率
    "max_heart_rate": pl.Float64,  # 最大心率
    "avg_cadence": pl.Float64,     # 平均步频
    "total_ascent": pl.Float64,    # 总爬升
    "total_descent": pl.Float64,   # 总下降
    "sport": pl.Utf8,              # 运动类型
}
```

### 4.2 索引文件

```json
// index.json
{
  "fingerprints": ["sha256_hash_1", "sha256_hash_2"],
  "metadata": {
    "files": {
      "sha256_hash_1": {
        "filename": "activity.fit",
        "filepath": "/path/to/activity.fit",
        "timestamp": "2024-01-01T08:00:00"
      }
    }
  }
}
```

---

## 5. 接口定义

### 5.1 RunnerTools 工具接口

```python
class RunnerTools:
    """Agent 工具集"""
    
    def get_running_stats(self, start_date: str, end_date: str) -> Dict[str, Any]:
        """获取指定日期范围的跑步统计"""
        pass
    
    def get_recent_runs(self, limit: int = 10) -> List[Dict[str, Any]]:
        """获取最近 N 次跑步记录"""
        pass
    
    def calculate_vdot_for_run(self, activity_id: str) -> float:
        """计算单次跑步的 VDOT 值"""
        pass
    
    def get_vdot_trend(self, days: int = 90) -> List[Dict[str, Any]]:
        """获取 VDOT 趋势数据"""
        pass
    
    def get_hr_drift_analysis(self, activity_id: str) -> Dict[str, Any]:
        """获取心率漂移分析"""
        pass
    
    def get_training_load(self, days: int = 42) -> Dict[str, Any]:
        """获取训练负荷数据（ATL/CTL/TSB）"""
        pass
```

### 5.2 CLI 命令接口

```bash
# 导入命令
nanobotrun import <path> [--force]

# 统计命令
nanobotrun stats [--year YYYY] [--start DATE] [--end DATE]

# Agent 交互
nanobotrun chat

# 版本信息
nanobotrun version
```

---

## 6. 验收标准汇总

### 6.1 功能验收

| 模块 | 验收项 | 通过标准 |
|------|--------|----------|
| 数据导入 | FIT 解析 | 100% 成功解析标准 FIT 文件 |
| 数据导入 | 去重机制 | 重复导入数据零增长 |
| 数据分析 | VDOT 计算 | 与标准表误差 < 2% |
| 数据分析 | TSS 计算 | 公式实现正确，误差 < 1% |
| CLI | 命令响应 | 启动 < 1s，查询 < 3s |

### 6.2 质量门禁

- 单元测试覆盖率 ≥ 80%
- 集成测试通过率 100%
- 代码风格检查（black, isort, mypy）全部通过
- 安全扫描（bandit）无高危漏洞

---

## 7. 附录

### 7.1 术语表

| 术语 | 定义 |
|------|------|
| VDOT | 跑力值（Velocity at VO2max），衡量跑者有氧能力的指标 |
| TSS | 训练压力分数（Training Stress Score） |
| ATL | 急性训练负荷（Acute Training Load），7 天平均 TSS |
| CTL | 慢性训练负荷（Chronic Training Load），42 天平均 TSS |
| TSB | 训练压力平衡（Training Stress Balance），CTL - ATL |
| FIT | Flexible and Interoperable Data Transfer，Garmin 设备数据格式 |

### 7.2 参考标准

- [Jack Daniels' VDOT Tables](https://vdoto2.com/)
- [TrainingPeaks TSS Calculation](https://help.trainingpeaks.com/hc/en-us/articles/204071584-Training-Stress-Score-TSS-)
- [FIT Protocol Specification](https://developer.garmin.com/fit/protocol/)

---

**文档维护**: 项目团队  
**审核状态**: 已审核  
**关联文档**: [用户需求文档](./REQ_用户需求文档.md)
