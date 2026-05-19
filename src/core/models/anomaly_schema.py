# 异常过滤规则统一定义
# 消除 profile.py 和 anomaly_filter.py 中的重复定义，单一数据源

from dataclasses import dataclass


@dataclass
class AnomalyFilterRule:
    """异常过滤规则数据结构

    Attributes:
        field_name: 字段名称
        condition: 条件表达式（如 ">", "<", ">=", "<=", "=="）
        threshold: 阈值
        action: 动作："filter" (过滤) 或 "clip" (截断)
        clip_value: 截断值（当 action 为 clip 时使用）
        description: 规则描述
    """

    field_name: str
    condition: str
    threshold: float
    action: str
    clip_value: float | None = None
    description: str | None = None


# 异常过滤规则配置（完整 11 条规则，单一数据源）
ANOMALY_FILTER_RULES: list[AnomalyFilterRule] = [
    # 心率异常过滤
    AnomalyFilterRule(
        field_name="avg_heart_rate",
        condition="<",
        threshold=30,
        action="filter",
        description="过滤平均心率过低的数据（< 30 bpm）",
    ),
    AnomalyFilterRule(
        field_name="avg_heart_rate",
        condition=">",
        threshold=220,
        action="filter",
        description="过滤平均心率过高的数据（> 220 bpm）",
    ),
    AnomalyFilterRule(
        field_name="max_heart_rate",
        condition="<",
        threshold=50,
        action="filter",
        description="过滤最大心率过低的数据（< 50 bpm）",
    ),
    AnomalyFilterRule(
        field_name="max_heart_rate",
        condition=">",
        threshold=250,
        action="filter",
        description="过滤最大心率过高的数据（> 250 bpm）",
    ),
    # 距离异常过滤
    AnomalyFilterRule(
        field_name="total_distance",
        condition="<",
        threshold=100,
        action="filter",
        description="过滤距离过短的数据（< 100 米）",
    ),
    AnomalyFilterRule(
        field_name="total_distance",
        condition=">",
        threshold=100000,
        action="filter",
        description="过滤距离过长的数据（> 100 公里）",
    ),
    # 时长异常过滤
    AnomalyFilterRule(
        field_name="total_timer_time",
        condition="<",
        threshold=60,
        action="filter",
        description="过滤时长过短的数据（< 1 分钟）",
    ),
    AnomalyFilterRule(
        field_name="total_timer_time",
        condition=">",
        threshold=28800,
        action="filter",
        description="过滤时长过长的数据（> 8 小时）",
    ),
    # 配速异常过滤（通过距离和时长计算）
    AnomalyFilterRule(
        field_name="pace_min_per_km",
        condition=">",
        threshold=20,
        action="filter",
        clip_value=20.0,
        description="过滤配速过慢的数据（> 20 min/km）",
    ),
    # VDOT 异常过滤
    AnomalyFilterRule(
        field_name="vdot",
        condition="<",
        threshold=20,
        action="filter",
        description="过滤 VDOT 过低的数据（< 20）",
    ),
    AnomalyFilterRule(
        field_name="vdot",
        condition=">",
        threshold=85,
        action="filter",
        description="过滤 VDOT 过高的数据（> 85）",
    ),
]
