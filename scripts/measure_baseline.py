"""Phase C 基线测量 - 指标计算与报告生成

读取预测记录和伤病报告，计算5项基线指标，
生成《Phase C 基线测量报告》Markdown文档。

用法:
    uv run python scripts/measure_baseline.py
    uv run python scripts/measure_baseline.py --output docs/product/Phase_C_基线测量报告.md
    uv run python scripts/measure_baseline.py --dry-run
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

# 将项目根目录加入sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


def parse_args() -> argparse.Namespace:
    """解析命令行参数"""
    parser = argparse.ArgumentParser(
        description="Phase C 基线测量 - 指标计算与报告生成"
    )
    parser.add_argument(
        "--output",
        type=str,
        default="docs/product/Phase_C_基线测量报告.md",
        help="报告输出路径",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="只显示指标，不生成报告文件",
    )
    return parser.parse_args()


def main() -> None:
    """主函数"""
    args = parse_args()

    print("=== Phase C 基线测量 ===\n")

    # 延迟导入
    from src.core.base.context import get_context

    context = get_context()
    prediction_engine = context.prediction_engine
    model_manager = prediction_engine._model_manager

    # 读取预测记录
    from src.core.prediction.model_manager import ModelManager

    assert isinstance(model_manager, ModelManager)

    all_records = model_manager.query_predictions()
    if not all_records:
        print("错误: 无预测记录。请先运行 generate_historical_predictions.py")
        sys.exit(1)

    # 读取伤病报告
    injury_dates = _load_injury_dates()

    # 计算各项指标
    metrics = _compute_metrics(all_records, injury_dates)

    # 显示指标
    _display_metrics(metrics)

    # 生成报告
    if not args.dry_run:
        output_path = Path(args.output)
        _generate_report(metrics, output_path, all_records)
        print(f"\n报告已生成: {output_path}")
    else:
        print("\n(dry-run 模式，未生成报告文件)")


def _load_injury_dates() -> list[str]:
    """加载伤病报告日期列表"""
    injury_labels_dir = Path.home() / ".nanobot-runner" / "injury_labels"
    if not injury_labels_dir.exists():
        return []

    dates: list[str] = []
    for label_file in injury_labels_dir.glob("*.json"):
        data = json.loads(label_file.read_text(encoding="utf-8"))
        dates.append(data["date"])
    return sorted(dates)


def _compute_metrics(records: list[Any], injury_dates: list[str]) -> dict[str, Any]:
    """计算5项基线指标"""
    metrics: dict[str, Any] = {}

    # 1. VDOT预测误差(MAE)
    vdot_records = [
        r
        for r in records
        if r.prediction_type == "vdot_trend" and r.actual_value is not None
    ]
    if vdot_records:
        errors = [
            abs(r.predicted_value - r.actual_value) / r.actual_value
            for r in vdot_records
            if r.actual_value and r.actual_value > 0
        ]
        metrics["vdot_mae"] = {
            "value": round(sum(errors) / len(errors) * 100, 2) if errors else None,
            "sample_count": len(vdot_records),
            "status": "measured",
        }
    else:
        metrics["vdot_mae"] = {
            "value": None,
            "sample_count": 0,
            "status": "no_data",
        }

    # 2. 全马成绩预测误差
    race_records = [
        r
        for r in records
        if r.prediction_type == "race_marathon" and r.actual_value is not None
    ]
    if race_records:
        errors = [
            abs(r.predicted_value - r.actual_value)
            for r in race_records
            if r.actual_value is not None
        ]
        metrics["race_marathon_error"] = {
            "value": round(sum(errors) / len(errors), 1) if errors else None,
            "unit": "seconds",
            "sample_count": len(race_records),
            "status": "measured",
        }
    else:
        metrics["race_marathon_error"] = {
            "value": None,
            "unit": "seconds",
            "sample_count": 0,
            "status": "no_data",
        }

    # 3. 用户主观满意度 — 待v0.23补充
    metrics["user_satisfaction"] = {
        "value": None,
        "sample_count": 0,
        "status": "pending_v023",
        "note": "待v0.23实现RecordFeedbackTool数据收集机制后补充",
    }

    # 4. 系统推荐采纳率 — 待v0.23补充
    metrics["recommendation_adoption"] = {
        "value": None,
        "sample_count": 0,
        "status": "pending_v023",
        "note": "待v0.23实现DecisionLog后补充",
    }

    # 5. 伤病预警召回率与误报率
    injury_records = [
        r
        for r in records
        if r.prediction_type == "injury_risk" and r.actual_value is not None
    ]
    if injury_records and injury_dates:
        # 召回率：实际伤病事件中，3周内有预警的比例
        hit_count = 0
        for inj_date_str in injury_dates:
            inj_date = datetime.fromisoformat(inj_date_str)
            # 检查伤病日期前21天内是否有预警（risk_score >= 60）
            for r in injury_records:
                pred_date = datetime.fromisoformat(r.prediction_date)
                if (
                    pred_date <= inj_date
                    and pred_date >= inj_date - timedelta(days=21)
                    and r.predicted_value >= 60.0
                ):
                    hit_count += 1
                    break

        recall = hit_count / len(injury_dates) * 100 if injury_dates else 0

        # 误报率：预警中未发生伤病的比例
        warnings = [r for r in injury_records if r.predicted_value >= 60.0]
        false_alarms = 0
        for r in warnings:
            pred_date = datetime.fromisoformat(r.prediction_date)
            has_injury = False
            for inj_date_str in injury_dates:
                inj_date = datetime.fromisoformat(inj_date_str)
                if pred_date <= inj_date <= pred_date + timedelta(days=21):
                    has_injury = True
                    break
            if not has_injury:
                false_alarms += 1

        false_alarm_rate = false_alarms / len(warnings) * 100 if warnings else 0

        metrics["injury_recall"] = {
            "value": round(recall, 1),
            "unit": "%",
            "sample_count": len(injury_dates),
            "status": "measured",
        }
        metrics["injury_false_alarm"] = {
            "value": round(false_alarm_rate, 1),
            "unit": "%",
            "sample_count": len(warnings),
            "status": "measured",
        }
    else:
        metrics["injury_recall"] = {
            "value": None,
            "unit": "%",
            "sample_count": 0,
            "status": "no_data",
        }
        metrics["injury_false_alarm"] = {
            "value": None,
            "unit": "%",
            "sample_count": 0,
            "status": "no_data",
        }

    return metrics


def _display_metrics(metrics: dict[str, Any]) -> None:
    """在终端显示指标"""
    print("--- 基线指标 ---\n")

    status_map = {
        "measured": "✅ 已测量",
        "no_data": "❌ 无数据",
        "pending_v023": "⏳ 待v0.23补充",
    }

    # VDOT MAE
    m = metrics["vdot_mae"]
    print(
        f"  VDOT预测误差(MAE): {m['value']}%"
        if m["value"] is not None
        else "  VDOT预测误差(MAE): —"
    )
    print(f"    样本量: {m['sample_count']}, 状态: {status_map[m['status']]}")

    # 全马预测误差
    m = metrics["race_marathon_error"]
    print(
        f"  全马成绩预测误差: {m['value']}秒"
        if m["value"] is not None
        else "  全马成绩预测误差: —"
    )
    print(f"    样本量: {m['sample_count']}, 状态: {status_map[m['status']]}")

    # 满意度
    m = metrics["user_satisfaction"]
    print("  用户主观满意度: —")
    print(f"    状态: {status_map[m['status']]}")

    # 采纳率
    m = metrics["recommendation_adoption"]
    print("  系统推荐采纳率: —")
    print(f"    状态: {status_map[m['status']]}")

    # 伤病召回率
    m = metrics["injury_recall"]
    print(
        f"  伤病预警召回率: {m['value']}%"
        if m["value"] is not None
        else "  伤病预警召回率: —"
    )
    print(f"    样本量: {m['sample_count']}, 状态: {status_map[m['status']]}")

    # 伤病误报率
    m = metrics["injury_false_alarm"]
    print(
        f"  伤病预警误报率: {m['value']}%"
        if m["value"] is not None
        else "  伤病预警误报率: —"
    )
    print(f"    样本量: {m['sample_count']}, 状态: {status_map[m['status']]}")


def _generate_report(
    metrics: dict[str, Any], output_path: Path, records: list[Any]
) -> None:
    """生成Markdown基线测量报告"""
    today = datetime.now().strftime("%Y-%m-%d")

    # 计算数据范围
    dates = [r.prediction_date for r in records]
    data_start = min(dates) if dates else "N/A"
    data_end = max(dates) if dates else "N/A"

    # 计算数据质量
    total_records = len(records)
    records_with_actual = sum(1 for r in records if r.actual_value is not None)
    backfill_rate = (
        round(records_with_actual / total_records * 100, 1) if total_records > 0 else 0
    )

    # 伤病报告数
    injury_labels_dir = Path.home() / ".nanobot-runner" / "injury_labels"
    injury_count = (
        len(list(injury_labels_dir.glob("*.json"))) if injury_labels_dir.exists() else 0
    )

    # 构建报告内容
    report = f"""# Phase C 基线测量报告

> 测量时间: {today}
> 数据范围: {data_start} ~ {data_end}
> 基线版本: v0.22.0

## 基线指标

| 指标 | 基线值 | 样本量 | 状态 |
|------|--------|--------|------|
| VDOT预测误差(MAE) | {_fmt(metrics["vdot_mae"], "%")} | {metrics["vdot_mae"]["sample_count"]} | {_status(metrics["vdot_mae"])} |
| 全马成绩预测误差 | {_fmt(metrics["race_marathon_error"], "秒")} | {metrics["race_marathon_error"]["sample_count"]} | {_status(metrics["race_marathon_error"])} |
| 用户主观满意度 | — | 0 | ⏳ 待v0.23补充 |
| 系统推荐采纳率 | — | 0 | ⏳ 待v0.23补充 |
| 伤病预警召回率 | {_fmt(metrics["injury_recall"], "%")} | {metrics["injury_recall"]["sample_count"]} | {_status(metrics["injury_recall"])} |
| 伤病预警误报率 | {_fmt(metrics["injury_false_alarm"], "%")} | {metrics["injury_false_alarm"]["sample_count"]} | {_status(metrics["injury_false_alarm"])} |

## 版本迭代目标

| 指标 | 基线值 | v0.23目标 | v0.24目标 | v0.25目标 |
|------|--------|-----------|-----------|-----------|
| VDOT预测误差(MAE) | {_fmt(metrics["vdot_mae"], "%")} | 下降≥5% | 下降≥5% | 下降≥5% |
| 全马成绩预测误差 | {_fmt(metrics["race_marathon_error"], "秒")} | 下降≥5% | 下降≥5% | 下降≥5% |
| 用户主观满意度 | — | ≥4.0/5.0 | +0.1 | +0.1 |
| 系统推荐采纳率 | — | >60% | +3% | +3% |
| 伤病预警召回率 | {_fmt(metrics["injury_recall"], "%")} | ≥75% | ≥75% | ≥75% |
| 伤病预警误报率 | {_fmt(metrics["injury_false_alarm"], "%")} | -3% | -3% | -3% |

## 数据质量说明

- 预测记录总数: {total_records}
- 实际值回填率: {backfill_rate}%
- 伤病报告总数: {injury_count}

## 测量方法说明

| 指标 | 测量方法 |
|------|---------|
| VDOT预测误差(MAE) | `abs(预测VDOT - 实际VDOT) / 实际VDOT`，取均值 |
| 全马成绩预测误差 | `abs(预测成绩 - 实际成绩)`，取均值 |
| 用户主观满意度 | `RecordFeedbackTool` 收集，1-5星评分 |
| 系统推荐采纳率 | `DecisionLog` 中 `recommendation_accepted` 字段统计 |
| 伤病预警召回率 | 对比 `InjuryRiskPrediction` 与 `InjuryReport` 时间戳，3周内预警命中比例 |
| 伤病预警误报率 | 预警但未发生伤病数 / 总预警数 |

---

> 本报告由 `scripts/measure_baseline.py` 自动生成
"""

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(report, encoding="utf-8")


def _fmt(metric: dict[str, Any], unit: str) -> str:
    """格式化指标值"""
    if metric["value"] is None:
        return "—"
    return f"{metric['value']}{unit}"


def _status(metric: dict[str, Any]) -> str:
    """获取指标状态标记"""
    status_map = {
        "measured": "✅ 已测量",
        "no_data": "❌ 无数据",
        "pending_v023": "⏳ 待v0.23补充",
    }
    return status_map.get(metric["status"], metric["status"])


if __name__ == "__main__":
    main()
