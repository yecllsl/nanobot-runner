"""Phase C 基线测量 - 历史预测生成脚本

遍历历史时间点，调用预测引擎生成PredictionRecord，
为基线测量提供数据基础。

用法:
    uv run python scripts/generate_historical_predictions.py
    uv run python scripts/generate_historical_predictions.py --start 2025-11-01 --end 2026-05-18
    uv run python scripts/generate_historical_predictions.py --type vdot
    uv run python scripts/generate_historical_predictions.py --reset
"""

from __future__ import annotations

import argparse
import sys
from datetime import datetime, timedelta
from pathlib import Path

# 将项目根目录加入sys.path，确保可以导入src模块
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


def parse_args() -> argparse.Namespace:
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description="Phase C 基线测量 - 历史预测生成")
    parser.add_argument(
        "--start",
        type=str,
        default=None,
        help="起始日期 (YYYY-MM-DD)，默认为6个月前",
    )
    parser.add_argument(
        "--end",
        type=str,
        default=None,
        help="结束日期 (YYYY-MM-DD)，默认为今天",
    )
    parser.add_argument(
        "--type",
        type=str,
        choices=["vdot", "race", "injury", "all"],
        default="all",
        help="预测类型 (vdot/race/injury/all)，默认all",
    )
    parser.add_argument(
        "--reset",
        action="store_true",
        help="清除已有预测记录并重新生成",
    )
    return parser.parse_args()


def main() -> None:
    """主函数"""
    args = parse_args()

    # 计算时间范围
    end_date = datetime.fromisoformat(args.end) if args.end else datetime.now()
    start_date = (
        datetime.fromisoformat(args.start)
        if args.start
        else end_date - timedelta(days=180)
    )

    print("=== Phase C 历史预测生成 ===")
    print(
        f"时间范围: {start_date.strftime('%Y-%m-%d')} ~ {end_date.strftime('%Y-%m-%d')}"
    )
    print(f"预测类型: {args.type}")
    print(f"重置模式: {args.reset}")
    print()

    # 延迟导入，避免模块加载时的副作用
    from src.core.base.context import get_context

    context = get_context()
    prediction_engine = context.prediction_engine
    model_manager = prediction_engine._model_manager

    # 重置模式：清除已有预测记录
    if args.reset:
        _reset_predictions(model_manager)

    # 生成历史预测
    _generate_predictions(
        prediction_engine=prediction_engine,
        model_manager=model_manager,
        session_repo=context.session_repo,
        start_date=start_date,
        end_date=end_date,
        prediction_type=args.type,
    )

    # 回填实际值
    _backfill_actuals(model_manager, args.type)

    print("\n=== 历史预测生成完成 ===")


def _reset_predictions(model_manager: object) -> None:
    """清除已有预测记录"""
    from src.core.prediction.model_manager import ModelManager

    assert isinstance(model_manager, ModelManager)
    predictions_dir = model_manager._models_dir / model_manager.PREDICTIONS_DIR_NAME
    if predictions_dir.exists():
        for pf in predictions_dir.glob("predictions_*.parquet"):
            pf.unlink()
            print(f"  已删除: {pf}")
    print("  预测记录已清除\n")


def _generate_predictions(
    prediction_engine: object,
    model_manager: object,
    session_repo: object,
    start_date: datetime,
    end_date: datetime,
    prediction_type: str,
) -> None:
    """按周遍历历史时间点，生成预测记录"""
    from src.core.prediction.model_manager import ModelManager
    from src.core.prediction.models import PredictionRecord

    assert isinstance(model_manager, ModelManager)

    # 按周生成时间点
    current = start_date
    time_points: list[datetime] = []
    while current <= end_date:
        time_points.append(current)
        current += timedelta(days=7)

    print(f"共 {len(time_points)} 个时间点待预测\n")

    # 统计计数
    vdot_count = 0
    race_count = 0
    injury_count = 0
    error_count = 0

    for i, tp in enumerate(time_points):
        date_str = tp.strftime("%Y-%m-%d")
        print(f"  [{i + 1}/{len(time_points)}] {date_str} ...", end=" ")

        try:
            # VDOT预测
            if prediction_type in ("vdot", "all"):
                vdot_pred = prediction_engine.predict_vdot_trend(days=7)
                record = PredictionRecord(
                    prediction_date=date_str,
                    prediction_type="vdot_trend",
                    predicted_value=vdot_pred.predicted_vdot,
                    predicted_unit="vdot",
                    actual_value=None,
                    deviation_pct=None,
                    prediction_method=vdot_pred.prediction_type,
                    model_version=vdot_pred.model_info.model_type
                    if vdot_pred.model_info
                    else "unknown",
                    confidence=vdot_pred.confidence,
                )
                model_manager.record_prediction(record)
                vdot_count += 1

            # 比赛成绩预测（全马）
            if prediction_type in ("race", "all"):
                race_pred = prediction_engine.predict_race_result(distance_km=42.195)
                record = PredictionRecord(
                    prediction_date=date_str,
                    prediction_type="race_marathon",
                    predicted_value=race_pred.predicted_time_seconds,
                    predicted_unit="seconds",
                    actual_value=None,
                    deviation_pct=None,
                    prediction_method=race_pred.prediction_type,
                    model_version="standard",
                    confidence=race_pred.confidence,
                )
                model_manager.record_prediction(record)
                race_count += 1

            # 伤病风险预测
            if prediction_type in ("injury", "all"):
                injury_pred = prediction_engine.predict_injury_risk(days=21)
                record = PredictionRecord(
                    prediction_date=date_str,
                    prediction_type="injury_risk",
                    predicted_value=injury_pred.risk_score,
                    predicted_unit="score",
                    actual_value=None,
                    deviation_pct=None,
                    prediction_method=injury_pred.prediction_type,
                    model_version="rule_based",
                    confidence=0.5,  # 规则基线默认置信度
                )
                model_manager.record_prediction(record)
                injury_count += 1

            print("OK")

        except Exception as e:
            print(f"FAILED ({e})")
            error_count += 1

    print("\n--- 生成统计 ---")
    print(f"  VDOT预测: {vdot_count} 条")
    print(f"  全马预测: {race_count} 条")
    print(f"  伤病预测: {injury_count} 条")
    print(f"  失败: {error_count} 条")


def _backfill_actuals(model_manager: object, prediction_type: str) -> None:
    """回填实际值并计算偏差

    使用自定义回填逻辑替代ModelManager.check_and_update_actual()，
    因为后者只查找预测日期当天的session，而预测日期不一定有训练。
    这里使用前后3天的时间窗口来匹配实际值。
    """
    from src.core.base.context import get_context
    from src.core.prediction.model_manager import ModelManager

    assert isinstance(model_manager, ModelManager)

    print("--- 回填实际值 ---")

    context = get_context()
    session_repo = context.session_repo

    # VDOT实际值回填：查找预测日期前后3天内最近的session的VDOT
    if prediction_type in ("vdot", "all"):
        vdot_count = _backfill_vdot_actuals(model_manager, session_repo)
        print(f"  vdot_trend: 更新了 {vdot_count} 条记录")

    # 全马成绩实际值回填：查找预测日期前后7天内的全马距离session
    if prediction_type in ("race", "all"):
        race_count = _backfill_race_actuals(model_manager, session_repo)
        print(f"  race_marathon: 更新了 {race_count} 条记录")

    # 伤病预测的实际值需要特殊处理（对比InjuryReport时间戳）
    if prediction_type in ("injury", "all"):
        injury_count = _backfill_injury_actuals(model_manager)
        print(f"  injury_risk: 更新了 {injury_count} 条记录")


def _backfill_vdot_actuals(model_manager: object, session_repo: object) -> int:
    """回填VDOT预测的实际值

    查找预测日期前后3天内最近的session，使用VDOT计算器计算实际VDOT
    """
    import polars as pl

    from src.core.calculators.vdot_calculator import VDOTCalculator
    from src.core.prediction.model_manager import ModelManager

    assert isinstance(model_manager, ModelManager)

    predictions_dir = model_manager._models_dir / model_manager.PREDICTIONS_DIR_NAME
    if not predictions_dir.exists():
        return 0

    calc = VDOTCalculator()
    updated_count = 0

    for pf in predictions_dir.glob("predictions_*.parquet"):
        df = pl.read_parquet(str(pf))
        vdot_pending = df.filter(
            (pl.col("prediction_type") == "vdot_trend")
            & pl.col("actual_value").is_null()
        )
        if vdot_pending.height == 0:
            continue

        rows = df.to_dicts()
        for row in rows:
            if (
                row["prediction_type"] != "vdot_trend"
                or row["actual_value"] is not None
            ):
                continue

            # 查找预测日期前后3天内的session
            pred_date = datetime.fromisoformat(row["prediction_date"])
            start = pred_date - timedelta(days=3)
            end = pred_date + timedelta(days=3)
            sessions = session_repo.get_sessions_by_date_range(start, end)

            if sessions:
                # 找距离最长的session计算VDOT（更可靠）
                best_session = max(sessions, key=lambda s: s.distance_km)
                distance_m = best_session.distance_km * 1000  # km转m
                duration_s = best_session.duration_min * 60  # min转s
                if distance_m >= 1500 and duration_s > 0:
                    actual_vdot = calc.calculate_vdot(distance_m, duration_s)
                    if actual_vdot > 0:
                        row["actual_value"] = actual_vdot
                        predicted = row["predicted_value"]
                        if predicted and predicted > 0:
                            row["deviation_pct"] = round(
                                abs(actual_vdot - predicted) / predicted * 100, 2
                            )
                        updated_count += 1

        df = pl.DataFrame(rows, schema=df.schema)
        df.write_parquet(str(pf))

    return updated_count


def _backfill_race_actuals(model_manager: object, session_repo: object) -> int:
    """回填全马预测的实际值

    查找预测日期前后7天内的全马距离session（40km-43km）
    """
    import polars as pl

    from src.core.prediction.model_manager import ModelManager

    assert isinstance(model_manager, ModelManager)

    predictions_dir = model_manager._models_dir / model_manager.PREDICTIONS_DIR_NAME
    if not predictions_dir.exists():
        return 0

    updated_count = 0

    for pf in predictions_dir.glob("predictions_*.parquet"):
        df = pl.read_parquet(str(pf))
        race_pending = df.filter(
            (pl.col("prediction_type") == "race_marathon")
            & pl.col("actual_value").is_null()
        )
        if race_pending.height == 0:
            continue

        rows = df.to_dicts()
        for row in rows:
            if (
                row["prediction_type"] != "race_marathon"
                or row["actual_value"] is not None
            ):
                continue

            # 查找预测日期前后7天内的全马距离session
            pred_date = datetime.fromisoformat(row["prediction_date"])
            start = pred_date - timedelta(days=7)
            end = pred_date + timedelta(days=7)
            sessions = session_repo.get_sessions_by_distance(40000, 43000)
            # 过滤日期范围
            matching = [
                s
                for s in sessions
                if start <= datetime.fromisoformat(s.timestamp) <= end
            ]

            if matching:
                best = matching[0]
                actual_seconds = best.duration_min * 60
                if actual_seconds > 0:
                    row["actual_value"] = actual_seconds
                    predicted = row["predicted_value"]
                    if predicted and predicted > 0:
                        row["deviation_pct"] = round(
                            abs(actual_seconds - predicted) / predicted * 100, 2
                        )
                    updated_count += 1

        df = pl.DataFrame(rows, schema=df.schema)
        df.write_parquet(str(pf))

    return updated_count


def _backfill_injury_actuals(model_manager: object) -> int:
    """回填伤病预测的实际值

    对比InjuryReport时间戳，3周内有伤病事件则actual_value=1，否则=0
    """
    import json

    import polars as pl

    from src.core.prediction.model_manager import ModelManager

    assert isinstance(model_manager, ModelManager)

    # 读取伤病报告
    injury_labels_dir = Path.home() / ".nanobot-runner" / "injury_labels"
    if not injury_labels_dir.exists():
        print("  无伤病报告数据，跳过伤病实际值回填")
        return 0

    injury_dates: list[str] = []
    for label_file in injury_labels_dir.glob("*.json"):
        data = json.loads(label_file.read_text(encoding="utf-8"))
        injury_dates.append(data["date"])

    if not injury_dates:
        return 0

    injury_dates_set = set(injury_dates)

    # 读取预测记录，回填伤病实际值
    predictions_dir = model_manager._models_dir / model_manager.PREDICTIONS_DIR_NAME
    if not predictions_dir.exists():
        return 0

    updated_count = 0
    for pf in predictions_dir.glob("predictions_*.parquet"):
        df = pl.read_parquet(str(pf))
        injury_rows = df.filter(pl.col("prediction_type") == "injury_risk")
        if injury_rows.height == 0:
            continue

        rows = df.to_dicts()
        for row in rows:
            if (
                row["prediction_type"] != "injury_risk"
                or row["actual_value"] is not None
            ):
                continue

            # 检查预测日期后21天内是否有伤病事件
            pred_date = datetime.fromisoformat(row["prediction_date"])
            has_injury = False
            for inj_date_str in injury_dates_set:
                inj_date = datetime.fromisoformat(inj_date_str)
                if pred_date <= inj_date <= pred_date + timedelta(days=21):
                    has_injury = True
                    break

            row["actual_value"] = 1.0 if has_injury else 0.0
            if row["predicted_value"] and row["predicted_value"] > 0:
                # 伤病预测：predicted是风险分数，actual是0/1
                # deviation_pct用风险分数与实际是否一致来衡量
                predicted_positive = row["predicted_value"] >= 60.0
                actual_positive = has_injury
                if predicted_positive != actual_positive:
                    row["deviation_pct"] = 100.0  # 预测方向错误
                else:
                    row["deviation_pct"] = 0.0  # 预测方向正确
            updated_count += 1

        df = pl.DataFrame(rows, schema=df.schema)
        df.write_parquet(str(pf))

    return updated_count


if __name__ == "__main__":
    main()
