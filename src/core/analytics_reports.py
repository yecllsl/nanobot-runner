# 报告生成模块
# 从 analytics.py 拆分出的报告生成相关函数
# 包含：每日晨报、问候语、昨日训练摘要、训练建议、周计划等

from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import TYPE_CHECKING, Any

import polars as pl

from src.core.base.exceptions import NanobotRunnerError
from src.core.models import DailyReportData

if TYPE_CHECKING:
    from src.core.analytics import AnalyticsEngine
    from src.core.storage.parquet_manager import StorageManager


def generate_greeting(hour: int, weekday: int) -> str:
    """根据时间和星期生成问候语

    Args:
        hour: 当前小时（0-23）
        weekday: 当前星期（0=周一，6=周日）

    Returns:
        str: 问候语
    """
    # 时间段问候
    if 5 <= hour < 9:
        time_greeting = "早上好"
    elif 9 <= hour < 12:
        time_greeting = "上午好"
    elif 12 <= hour < 14:
        time_greeting = "中午好"
    elif 14 <= hour < 18:
        time_greeting = "下午好"
    else:
        time_greeting = "晚上好"

    # 根据星期添加训练提示
    if weekday == 0:  # 周一
        return f"{time_greeting}！新的一周开始了，让我们制定训练计划吧。"
    elif weekday == 6:  # 周日
        return f"{time_greeting}！今天是休息日，好好恢复吧。"
    else:
        return f"{time_greeting}！今天是您的训练日。"


def get_yesterday_run(
    storage: StorageManager,
    calculate_tss_for_run_func: Any,
    yesterday: date,
) -> dict[str, Any] | None:
    """获取昨日训练摘要

    从存储中读取昨日跑步数据，汇总距离、时长、TSS等信息。

    Args:
        storage: StorageManager实例，用于读取数据
        calculate_tss_for_run_func: TSS计算函数（engine.calculate_tss_for_run）
        yesterday: 昨日日期对象

    Returns:
        Optional[Dict]: 昨日训练数据，无训练返回None
            - distance_km: 距离（公里）
            - duration_min: 时长（分钟）
            - tss: 训练压力分数
            - run_count: 跑步次数
    """
    try:
        lf = storage.read_parquet()

        # 处理空数据情况（无数据文件时返回空LazyFrame）
        if lf.collect_schema().names() == []:
            return None

        # 过滤昨日的数据
        start_of_yesterday = datetime.combine(yesterday, datetime.min.time())
        end_of_yesterday = datetime.combine(yesterday, datetime.max.time())

        df = lf.filter(
            pl.col("timestamp").is_between(start_of_yesterday, end_of_yesterday)
        ).collect()

        if df.is_empty():
            return None

        # 计算昨日训练汇总
        total_distance = df["session_total_distance"].sum()
        total_duration = df["session_total_timer_time"].sum()

        # 计算TSS
        tss_values = []
        for row in df.iter_rows(named=True):
            tss = calculate_tss_for_run_func(
                distance_m=row.get("session_total_distance") or 0,
                duration_s=row.get("session_total_timer_time") or 0,
                avg_heart_rate=row.get("session_avg_heart_rate"),
            )
            tss_values.append(tss)
        total_tss = sum(tss_values)

        return {
            "distance_km": round(total_distance / 1000, 2),
            "duration_min": round(total_duration / 60, 1),
            "tss": round(total_tss, 1),
            "run_count": df.height,
        }
    except NanobotRunnerError:
        return None


def generate_training_advice(
    fitness_status: dict[str, Any],
    yesterday_run: dict[str, Any] | None,
    weekday: int,
    _age: int,
) -> str:
    """基于训练负荷数据生成训练建议

    综合考虑TSB状态、昨日训练强度、CTL体能基础等因素，
    生成个性化的训练建议文本。

    Args:
        fitness_status: 体能状态数据（包含tsb/fitness_status/ctl等字段）
        yesterday_run: 昨日训练数据（可为None）
        weekday: 当前星期（0=周一，6=周日）
        _age: 年龄

    Returns:
        str: 训练建议文本
    """
    tsb = fitness_status.get("tsb", 0.0)
    status = fitness_status.get("fitness_status", "数据不足")
    ctl = fitness_status.get("ctl", 0.0)

    advice_parts: list[str] = []

    # 基于TSB状态生成建议
    if status == "数据不足":
        advice_parts.append("暂无足够数据生成个性化建议，请先导入更多训练数据。")
        advice_parts.append("建议开始规律训练，每次训练都记录心率数据。")
    elif tsb > 10:
        advice_parts.append("状态良好，可以进行中等强度训练。")
        if weekday in [1, 3, 5]:  # 周二、周四、周六
            advice_parts.append("建议进行 8-10 公里的节奏跑，保持心率在区间3。")
        elif weekday in [2, 4]:  # 周三、周五
            advice_parts.append("建议进行轻松跑 6-8 公里，保持心率在区间2。")
        else:
            advice_parts.append("可以进行长距离慢跑或交叉训练。")
    elif tsb > 0:
        advice_parts.append("状态正常，可以保持正常训练节奏。")
        advice_parts.append("建议进行 6-8 公里的轻松跑，注意监控身体反应。")
    elif tsb > -10:
        advice_parts.append("有一定训练累积疲劳，建议适当降低强度。")
        advice_parts.append("建议进行轻松跑或交叉训练，保证充足休息。")
    else:
        advice_parts.append("警告：疲劳累积过多，建议安排休息日。")
        advice_parts.append("建议进行 2-3 天轻松活动或完全休息。")

    # 考虑昨日训练情况
    if yesterday_run:
        if yesterday_run["tss"] > 100:
            advice_parts.append(
                f"昨日训练强度较高（TSS: {yesterday_run['tss']}），注意恢复。"
            )
        elif yesterday_run["tss"] > 50:
            advice_parts.append("昨日进行了中等强度训练，今日可适度活动。")

    # 基于CTL补充建议
    if ctl < 30:
        advice_parts.append("体能基础较弱，建议循序渐进增加训练量。")
    elif ctl > 80:
        advice_parts.append("体能基础扎实，可保持当前训练水平。")

    return " ".join(advice_parts)


def get_daily_plan(weekday: int, tsb: float, _ctl: float, is_past: bool) -> str:
    """获取单日训练计划

    根据TSB（训练压力平衡）和星期几，生成每日训练计划。
    TSB越低，训练量越小，休息日越多。

    Args:
        weekday: 星期几（0=周一，6=周日）
        tsb: 训练压力平衡
        _ctl: 慢性训练负荷
        is_past: 是否已过去

    Returns:
        str: 训练计划
    """
    if is_past:
        return "已完成"

    # 基于TSB调整训练计划
    if tsb < -10:
        # 过度训练状态，减少训练量
        plans = {
            0: "休息",
            1: "轻松跑 4km",
            2: "休息",
            3: "轻松跑 5km",
            4: "休息",
            5: "轻松跑 4km",
            6: "休息",
        }
    elif tsb < 0:
        # 轻度疲劳状态
        plans = {
            0: "休息",
            1: "轻松跑 6km",
            2: "节奏跑 8km",
            3: "轻松跑 5km",
            4: "间歇跑 6km",
            5: "轻松跑 6km",
            6: "休息",
        }
    else:
        # 状态良好
        plans = {
            0: "休息",
            1: "轻松跑 6km",
            2: "节奏跑 8km",
            3: "轻松跑 5km",
            4: "间歇跑 8km",
            5: "轻松跑 6km",
            6: "长距离跑 15km",
        }

    return plans.get(weekday, "休息")


def generate_weekly_plan(
    today: date, fitness_status: dict[str, Any], _age: int
) -> list[dict[str, Any]]:
    """生成本周训练计划预览

    从周一开始，根据TSB和CTL状态，为每天生成训练计划。

    Args:
        today: 今日日期对象
        fitness_status: 体能状态数据（包含tsb/ctl等字段）
        _age: 年龄

    Returns:
        List[Dict]: 每日训练计划列表，每项包含day/date/plan/is_today/is_past
    """
    weekday_names = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
    tsb = fitness_status.get("tsb", 0.0)
    ctl = fitness_status.get("ctl", 0.0)

    # 获取本周一的日期
    monday = today - timedelta(days=today.weekday())

    weekly_plan: list[dict[str, Any]] = []

    for i in range(7):
        current_date = monday + timedelta(days=i)
        weekday_name = weekday_names[i]
        is_today = current_date == today
        is_past = current_date < today

        # 根据TSB和星期生成计划
        plan = get_daily_plan(i, tsb, ctl, is_past)
        weekly_plan.append(
            {
                "day": weekday_name,
                "date": current_date.strftime("%m/%d"),
                "plan": plan,
                "is_today": is_today,
                "is_past": is_past,
            }
        )

    return weekly_plan


def generate_daily_report(engine: AnalyticsEngine, age: int = 30) -> DailyReportData:
    """生成每日晨报内容

    包含：
    - 日期和问候语
    - 昨日训练摘要（如有）
    - 当前体能状态（ATL/CTL/TSB）
    - 训练建议
    - 本周训练计划预览

    Args:
        engine: AnalyticsEngine实例，用于获取训练负荷等数据
        age: 年龄，用于计算最大心率和训练建议

    Returns:
        DailyReportData: 晨报内容
    """
    # 获取当前日期
    now = datetime.now()
    today = now.date()
    yesterday = today - timedelta(days=1)

    # 星期映射
    weekday_names = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]

    # 1. 生成日期和问候语
    date_str = (
        f"{today.year}年{today.month}月{today.day}日 {weekday_names[today.weekday()]}"
    )
    greeting = generate_greeting(now.hour, today.weekday())

    # 2. 获取昨日训练摘要
    yesterday_run = get_yesterday_run(
        engine.storage, engine.calculate_tss_for_run, yesterday
    )

    # 3. 获取体能状态
    fitness_status = engine.get_training_load(days=42)

    # 4. 生成训练建议
    training_advice = generate_training_advice(
        fitness_status, yesterday_run, today.weekday(), age
    )

    # 5. 生成本周训练计划预览
    weekly_plan = generate_weekly_plan(today, fitness_status, age)

    return DailyReportData(
        date=date_str,
        greeting=greeting,
        yesterday_run=yesterday_run,
        fitness_status={
            "atl": fitness_status.get("atl", 0.0),
            "ctl": fitness_status.get("ctl", 0.0),
            "tsb": fitness_status.get("tsb", 0.0),
            "status": fitness_status.get("fitness_status", "数据不足"),
        },
        training_advice=training_advice,
        weekly_plan=weekly_plan,
        generated_at=now.isoformat(),
    )
