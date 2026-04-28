# 偏好管理命令
# 提供用户偏好的查看、更新、重置等管理功能

import typer

from src.cli.common import console, print_error

app = typer.Typer(help="偏好管理命令")


def _get_preference_learner():
    """获取偏好学习器实例"""
    from src.core.base.context import AppContextFactory
    from src.core.personality import PreferenceLearner, UserPreferences

    context = AppContextFactory.create()
    profile_storage = context.profile_storage

    preferences = UserPreferences.default()
    try:
        profile = profile_storage.load_profile_json()
        if profile is not None:
            profile_dict = profile.to_dict() if hasattr(profile, "to_dict") else {}
            pref_data = profile_dict.get("preferences", {})
            if pref_data:
                preferences = UserPreferences.from_dict(pref_data)
    except Exception:
        pass

    return PreferenceLearner(preferences=preferences), profile_storage


@app.command("show")
def show_preferences() -> None:
    """查看当前用户偏好

    显示训练时段、强度偏好、沟通风格等偏好设置。
    """
    try:
        learner, _ = _get_preference_learner()
        preferences = learner.get_learned_preferences()
        pref_dict = preferences.to_dict()

        console.print("[bold]当前用户偏好[/bold]\n")

        preference_labels = {
            "training_time": "训练时段",
            "training_intensity": "训练强度",
            "communication_style": "沟通风格",
            "suggestion_frequency": "建议频率",
            "detail_preference": "详细程度",
            "pace_preference": "配速偏好",
            "distance_preference": "距离偏好",
            "weather_sensitivity": "天气敏感度",
        }

        value_labels = {
            "morning": "早晨",
            "afternoon": "下午",
            "evening": "晚上",
            "low": "低",
            "medium": "中等",
            "high": "高",
            "brief": "简洁",
            "detailed": "详细",
            "encouraging": "鼓励",
            "analytical": "分析",
            "minimal": "最少",
            "moderate": "适中",
            "frequent": "频繁",
            "concise": "精简",
            "standard": "标准",
        }

        for key, label in preference_labels.items():
            value = pref_dict.get(key, "")
            display_value = value_labels.get(value, value)
            console.print(f"  [cyan]{label}[/cyan]: {display_value}")

        if pref_dict.get("custom_preferences"):
            console.print("\n  [bold]自定义偏好[/bold]")
            for k, v in pref_dict["custom_preferences"].items():
                console.print(f"    [cyan]{k}[/cyan]: {v}")

    except Exception as e:
        print_error(f"获取偏好失败: {e}")
        raise typer.Exit(1)


@app.command("set")
def set_preference(
    key: str = typer.Argument(help="偏好字段名"),
    value: str = typer.Argument(help="偏好值"),
) -> None:
    """设置用户偏好

    支持的偏好字段:
    - training_time: morning/afternoon/evening
    - training_intensity: low/medium/high
    - communication_style: brief/detailed/encouraging/analytical
    - suggestion_frequency: minimal/moderate/frequent
    - detail_preference: concise/standard/detailed
    - weather_sensitivity: low/medium/high
    """
    valid_fields = {
        "training_time": ["morning", "afternoon", "evening"],
        "training_intensity": ["low", "medium", "high"],
        "communication_style": ["brief", "detailed", "encouraging", "analytical"],
        "suggestion_frequency": ["minimal", "moderate", "frequent"],
        "detail_preference": ["concise", "standard", "detailed"],
        "weather_sensitivity": ["low", "medium", "high"],
    }

    if key not in valid_fields:
        print_error(
            f"无效的偏好字段: {key}\n支持的字段: {', '.join(valid_fields.keys())}"
        )
        raise typer.Exit(1)

    valid_values = valid_fields[key]
    if value not in valid_values:
        print_error(
            f"无效的偏好值: {value}\n字段 '{key}' 支持的值: {', '.join(valid_values)}"
        )
        raise typer.Exit(1)

    try:
        learner, profile_storage = _get_preference_learner()
        new_preferences = learner.update_preference_model({key: value})

        try:
            profile = profile_storage.load_profile_json()
            if profile is not None and hasattr(profile, "to_dict"):
                profile_dict = profile.to_dict()
            else:
                profile_dict = {}
            profile_dict["preferences"] = new_preferences.to_dict()
            if hasattr(profile_storage, "save_profile_json"):
                profile_storage.save_profile_json(profile_dict)
        except Exception:
            pass

        console.print(f"[green]偏好已更新: {key} = {value}[/green]")

    except Exception as e:
        print_error(f"更新偏好失败: {e}")
        raise typer.Exit(1)


@app.command("reset")
def reset_preferences() -> None:
    """重置偏好到默认值

    清除所有学习到的偏好，恢复为默认设置。
    """
    try:
        learner, profile_storage = _get_preference_learner()
        new_preferences = learner.reset_preferences()

        try:
            profile = profile_storage.load_profile_json()
            if profile is not None and hasattr(profile, "to_dict"):
                profile_dict = profile.to_dict()
            else:
                profile_dict = {}
            profile_dict["preferences"] = new_preferences.to_dict()
            if hasattr(profile_storage, "save_profile_json"):
                profile_storage.save_profile_json(profile_dict)
        except Exception:
            pass

        console.print("[green]偏好已重置为默认值[/green]")

    except Exception as e:
        print_error(f"重置偏好失败: {e}")
        raise typer.Exit(1)


@app.command("feedback-stats")
def feedback_stats() -> None:
    """查看反馈统计

    显示偏好学习的反馈统计数据。
    """
    try:
        learner, _ = _get_preference_learner()
        stats = learner.get_feedback_stats()

        console.print("[bold]反馈统计[/bold]\n")
        console.print(f"  总反馈数: {stats['total_feedback']}")
        console.print(f"  正面反馈: {stats['positive_count']}")
        console.print(f"  负面反馈: {stats['negative_count']}")
        console.print(f"  中性反馈: {stats['neutral_count']}")
        console.print(f"  修正反馈: {stats['correction_count']}")

        if stats["category_distribution"]:
            console.print("\n  [bold]偏好类别分布[/bold]")
            for cat, count in stats["category_distribution"].items():
                console.print(f"    {cat}: {count}")

    except Exception as e:
        print_error(f"获取反馈统计失败: {e}")
        raise typer.Exit(1)
