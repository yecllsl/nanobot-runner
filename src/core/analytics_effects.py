# 训练效果计算模块
# 从 analytics.py 拆分出的训练效果相关计算函数
# 包含：心率区间计算、区间时长统计、有氧/无氧效果计算、恢复时间估算

from __future__ import annotations


def calculate_hr_zones(max_hr: int) -> dict[str, tuple[int, int]]:
    """计算心率区间边界

    基于最大心率的百分比划分5个心率区间：
    - zone1: 恢复区 (50%-60%)
    - zone2: 有氧基础区 (60%-70%)
    - zone3: 有氧耐力区 (70%-80%)
    - zone4: 乳酸阈值区 (80%-90%)
    - zone5: 无氧耐力区 (90%-100%)

    Args:
        max_hr: 最大心率

    Returns:
        dict: 心率区间边界字典，key为zone1-zone5，value为(下限, 上限)元组
    """
    return {
        "zone1": (int(max_hr * 0.50), int(max_hr * 0.60)),  # 恢复区
        "zone2": (int(max_hr * 0.60), int(max_hr * 0.70)),  # 有氧基础区
        "zone3": (int(max_hr * 0.70), int(max_hr * 0.80)),  # 有氧耐力区
        "zone4": (int(max_hr * 0.80), int(max_hr * 0.90)),  # 乳酸阈值区
        "zone5": (int(max_hr * 0.90), int(max_hr * 1.00)),  # 无氧耐力区
    }


def calculate_zone_time(
    heart_rate_data: list[int], hr_zones: dict[str, tuple[int, int]]
) -> dict[str, int]:
    """计算各心率区间的时长（秒）

    遍历秒级心率数据，统计每个心率区间内的数据点数量（即秒数）。

    Args:
        heart_rate_data: 心率数据列表（每秒一个数据点）
        hr_zones: 心率区间边界，由 calculate_hr_zones() 生成

    Returns:
        dict: 各区间时长（秒），key为zone1-zone5
    """
    zone_time: dict[str, int] = {
        "zone1": 0,
        "zone2": 0,
        "zone3": 0,
        "zone4": 0,
        "zone5": 0,
    }

    if not heart_rate_data:
        return zone_time

    for hr in heart_rate_data:
        if hr < hr_zones["zone1"][0]:
            continue
        elif hr < hr_zones["zone1"][1]:
            zone_time["zone1"] += 1
        elif hr < hr_zones["zone2"][1]:
            zone_time["zone2"] += 1
        elif hr < hr_zones["zone3"][1]:
            zone_time["zone3"] += 1
        elif hr < hr_zones["zone4"][1]:
            zone_time["zone4"] += 1
        else:
            zone_time["zone5"] += 1

    return zone_time


def calculate_training_effect(
    total_duration: int,
    zone_times: dict[str, int],
    weights: dict[str, float],
    scale: float,
) -> float:
    """训练效果通用计算方法

    根据心率区间加权时长占比，映射到 1.0-5.0 的训练效果值。

    计算逻辑：
    1. 计算加权时长 = sum(区间时长 * 权重)
    2. 计算占比 = 加权时长 / 总时长
    3. 映射到效果值 = 1.0 + 占比 * 比例系数
    4. 限制在 1.0-5.0 范围内

    Args:
        total_duration: 总时长（秒）
        zone_times: 各心率区间时长
        weights: 各区间权重，如 {"zone2": 0.8, "zone3": 1.0}
        scale: 映射比例系数（有氧 4.0，无氧 6.67）

    Returns:
        float: 训练效果值（1.0-5.0）
    """
    if total_duration == 0:
        return 1.0

    # 计算加权时长
    weighted_time = sum(
        zone_times.get(zone, 0) * weight for zone, weight in weights.items()
    )

    # 计算占比并映射到 1.0-5.0 范围
    ratio = weighted_time / total_duration
    effect = 1.0 + ratio * scale

    return round(min(max(effect, 1.0), 5.0), 1)


def calculate_aerobic_effect(zone_time: dict[str, int], total_duration: int) -> float:
    """计算有氧训练效果（1.0-5.0）

    有氧效果基于心率区间2-3的时间占比：
    - 区间2（有氧基础）: 权重0.8
    - 区间3（有氧耐力）: 权重1.0

    Args:
        zone_time: 各区间时长
        total_duration: 总时长（秒）

    Returns:
        float: 有氧效果值（1.0-5.0）
    """
    return calculate_training_effect(
        total_duration=total_duration,
        zone_times=zone_time,
        weights={"zone2": 0.8, "zone3": 1.0},
        scale=4.0,
    )


def calculate_anaerobic_effect(zone_time: dict[str, int], total_duration: int) -> float:
    """计算无氧训练效果（1.0-5.0）

    无氧效果基于心率区间4-5的时间占比：
    - 区间4（乳酸阈值）: 权重0.8
    - 区间5（无氧耐力）: 权重1.2

    Args:
        zone_time: 各区间时长
        total_duration: 总时长（秒）

    Returns:
        float: 无氧效果值（1.0-5.0）
    """
    return calculate_training_effect(
        total_duration=total_duration,
        zone_times=zone_time,
        weights={"zone4": 0.8, "zone5": 1.2},
        scale=6.67,
    )


def calculate_recovery_time(
    aerobic_effect: float,
    anaerobic_effect: float,
    duration_s: float,
    avg_heart_rate: float,
    max_hr: int,
) -> int:
    """计算恢复时间（小时）

    基于训练效果、时长和心率强度估算恢复时间。

    计算逻辑：
    1. 基础恢复时间 = (有氧效果 + 无氧效果) / 2 * 12（最大60小时）
    2. 时长因子 = 1.0 + (时长秒 / 1800) * 0.1（每30分钟增加10%）
    3. 心率强度因子 = 1.0 + (心率强度 - 0.5) * 0.5
    4. 综合恢复时间 = 基础 * 时长因子 * 心率因子
    5. 限制在6-72小时范围内

    Args:
        aerobic_effect: 有氧效果值
        anaerobic_effect: 无氧效果值
        duration_s: 训练时长（秒）
        avg_heart_rate: 平均心率
        max_hr: 最大心率

    Returns:
        int: 恢复时间（小时），范围6-72
    """
    # 基础恢复时间（基于训练效果）
    base_recovery = (aerobic_effect + anaerobic_effect) / 2 * 12  # 最大60小时

    # 时长因子（每30分钟增加10%恢复时间）
    duration_factor = 1.0 + (duration_s / 1800) * 0.1

    # 心率强度因子
    hr_intensity = avg_heart_rate / max_hr if max_hr > 0 else 0.5
    hr_factor = 1.0 + (hr_intensity - 0.5) * 0.5

    # 综合计算
    recovery_hours = base_recovery * duration_factor * hr_factor

    # 限制在6-72小时范围内
    return int(min(max(recovery_hours, 6), 72))
