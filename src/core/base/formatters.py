# 统一格式化工具函数
# 消除 formatter.py / statistics_aggregator.py / race_predictor.py 中的重复格式化逻辑


def format_duration_hms(duration_s: float) -> str:
    """格式化时长为 HH:MM:SS 格式

    核心层格式化函数，适用于数据存储、报表等需要标准化格式的场景。

    Args:
        duration_s: 时长（秒）

    Returns:
        str: 格式化后的时长字符串，如 "01:30:00"
    """
    try:
        hours = int(duration_s // 3600)
        minutes = int((duration_s % 3600) // 60)
        seconds = int(duration_s % 60)
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
    except (TypeError, ValueError):
        return "00:00:00"


def format_duration_human(seconds: int | float) -> str:
    """格式化时长为人类可读的中文格式

    CLI 层格式化函数，适用于终端展示等需要可读性的场景。

    Args:
        seconds: 秒数

    Returns:
        str: 格式化后的时长字符串，如 "1小时30分0秒"
    """
    seconds = int(seconds)
    if seconds < 60:
        return f"{seconds}秒"
    elif seconds < 3600:
        minutes = seconds // 60
        secs = seconds % 60
        return f"{minutes}分{secs}秒"
    else:
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        secs = seconds % 60
        return f"{hours}小时{minutes}分{secs}秒"


def format_pace(seconds_per_km: float) -> str:
    """格式化配速为 M'SS" 格式

    统一配速格式化函数，适用于所有场景。

    Args:
        seconds_per_km: 每公里秒数

    Returns:
        str: 格式化后的配速字符串，如 "5'00\""；无效值返回 "0'00\""
    """
    try:
        if seconds_per_km is None or seconds_per_km <= 0:
            return "0'00\""
        minutes = int(seconds_per_km // 60)
        seconds = int(seconds_per_km % 60)
        return f"{minutes}'{seconds:02d}\""
    except (TypeError, ValueError):
        return "0'00\""


def format_pace_with_unit(seconds_per_km: float) -> str:
    """格式化配速为 M'SS"/km 格式（带单位）

    适用于比赛预测等需要明确单位的场景。

    Args:
        seconds_per_km: 每公里秒数

    Returns:
        str: 格式化后的配速字符串，如 "5'00\"/km"
    """
    return f"{format_pace(seconds_per_km)}/km"


def format_pace_cli(seconds_per_km: float) -> str:
    """CLI 层配速格式化，无效值返回 "N/A"

    Args:
        seconds_per_km: 每公里秒数

    Returns:
        str: 格式化后的配速字符串，如 "5'00\""；无效值返回 "N/A"
    """
    if seconds_per_km <= 0:
        return "N/A"
    return format_pace(seconds_per_km)
