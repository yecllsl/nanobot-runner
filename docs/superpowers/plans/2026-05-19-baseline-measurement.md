# Phase C 基线测量脚本 实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 开发两个独立Python脚本，对v0.22现有数据进行回溯预测和基线测量，生成《Phase C 基线测量报告》。

**Architecture:** 两阶段执行 — 阶段1脚本遍历历史时间点调用预测引擎生成PredictionRecord，阶段2脚本读取预测记录和伤病报告计算5项指标并输出Markdown报告。两个脚本通过 `~/.nanobot-runner/models/predictions/` Parquet文件传递数据。

**Tech Stack:** Python 3.11+, Polars, argparse, 项目现有预测引擎

---

## File Structure

| 文件 | 职责 |
|------|------|
| `scripts/generate_historical_predictions.py` | 遍历历史时间点，调用预测引擎，写入PredictionRecord |
| `scripts/measure_baseline.py` | 读取预测记录和伤病报告，计算指标，生成Markdown报告 |

---

### Task 1: 历史预测生成脚本 - 框架与参数解析

**Files:**
- Create: `scripts/generate_historical_predictions.py`

- [ ] **Step 1: 创建脚本框架，包含参数解析和主函数结构**

```python
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
    parser = argparse.ArgumentParser(
        description="Phase C 基线测量 - 历史预测生成"
    )
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
    end_date = (
        datetime.fromisoformat(args.end)
        if args.end
        else datetime.now()
    )
    start_date = (
        datetime.fromisoformat(args.start)
        if args.start
        else end_date - timedelta(days=180)
    )

    print(f"=== Phase C 历史预测生成 ===")
    print(f"时间范围: {start_date.strftime('%Y-%m-%d')} ~ {end_date.strftime('%Y-%m-%d')}")
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
    """生成历史预测"""
    # 占位，Task 2 实现
    pass


def _backfill_actuals(model_manager: object, prediction_type: str) -> None:
    """回填实际值"""
    # 占位，Task 3 实现
    pass


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: 运行脚本验证参数解析**

Run: `uv run python scripts/generate_historical_predictions.py --help`
Expected: 显示帮助信息，包含 --start, --end, --type, --reset 参数

- [ ] **Step 3: Commit**

```bash
git add scripts/generate_historical_predictions.py
git commit -m "feat(baseline): add historical prediction generation script skeleton"
```

---

### Task 2: 历史预测生成脚本 - 核心预测生成逻辑

**Files:**
- Modify: `scripts/generate_historical_predictions.py`

- [ ] **Step 1: 实现 `_generate_predictions` 函数**

替换 `_generate_predictions` 的占位实现：

```python
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
        print(f"  [{i+1}/{len(time_points)}] {date_str} ...", end=" ")

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
                race_pred = prediction_engine.predict_race_result(
                    distance_km=42.195
                )
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

    print(f"\n--- 生成统计 ---")
    print(f"  VDOT预测: {vdot_count} 条")
    print(f"  全马预测: {race_count} 条")
    print(f"  伤病预测: {injury_count} 条")
    print(f"  失败: {error_count} 条")
```

- [ ] **Step 2: 运行脚本验证预测生成（dry run，仅1周）**

Run: `uv run python scripts/generate_historical_predictions.py --start 2026-05-11 --end 2026-05-18 --type vdot`
Expected: 输出1个时间点的VDOT预测结果，无报错

- [ ] **Step 3: Commit**

```bash
git add scripts/generate_historical_predictions.py
git commit -m "feat(baseline): implement historical prediction generation logic"
```

---

### Task 3: 历史预测生成脚本 - 实际值回填

**Files:**
- Modify: `scripts/generate_historical_predictions.py`

- [ ] **Step 1: 实现 `_backfill_actuals` 函数**

替换 `_backfill_actuals` 的占位实现：

```python
def _backfill_actuals(model_manager: object, prediction_type: str) -> None:
    """回填实际值并计算偏差"""
    from src.core.prediction.model_manager import ModelManager

    assert isinstance(model_manager, ModelManager)

    print("--- 回填实际值 ---")

    types_to_update = []
    if prediction_type in ("vdot", "all"):
        types_to_update.append("vdot_trend")
    if prediction_type in ("race", "all"):
        types_to_update.append("race_marathon")

    for pt in types_to_update:
        count = model_manager.check_and_update_actual(pt)
        print(f"  {pt}: 更新了 {count} 条记录")

    # 伤病预测的实际值需要特殊处理（对比InjuryReport时间戳）
    if prediction_type in ("injury", "all"):
        injury_count = _backfill_injury_actuals(model_manager)
        print(f"  injury_risk: 更新了 {injury_count} 条记录")


def _backfill_injury_actuals(model_manager: object) -> int:
    """回填伤病预测的实际值

    对比InjuryReport时间戳，3周内有伤病事件则actual_value=1，否则=0
    """
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
        import json
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
            if row["prediction_type"] != "injury_risk" or row["actual_value"] is not None:
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
```

- [ ] **Step 2: 运行完整脚本验证**

Run: `uv run python scripts/generate_historical_predictions.py --reset`
Expected: 生成约26个时间点的预测记录，回填实际值，无报错

- [ ] **Step 3: Commit**

```bash
git add scripts/generate_historical_predictions.py
git commit -m "feat(baseline): implement actual value backfill for predictions"
```

---

### Task 4: 基线测量脚本 - 框架与指标计算

**Files:**
- Create: `scripts/measure_baseline.py`

- [ ] **Step 1: 创建完整的基线测量脚本**

```python
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


def _compute_metrics(
    records: list[Any], injury_dates: list[str]
) -> dict[str, Any]:
    """计算5项基线指标"""
    metrics: dict[str, Any] = {}

    # 1. VDOT预测误差(MAE)
    vdot_records = [
        r for r in records
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
        r for r in records
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
        r for r in records
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

        false_alarm_rate = (
            false_alarms / len(warnings) * 100 if warnings else 0
        )

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
    print(f"  VDOT预测误差(MAE): {m['value']}%" if m['value'] is not None else "  VDOT预测误差(MAE): —")
    print(f"    样本量: {m['sample_count']}, 状态: {status_map[m['status']]}")

    # 全马预测误差
    m = metrics["race_marathon_error"]
    print(f"  全马成绩预测误差: {m['value']}秒" if m['value'] is not None else "  全马成绩预测误差: —")
    print(f"    样本量: {m['sample_count']}, 状态: {status_map[m['status']]}")

    # 满意度
    m = metrics["user_satisfaction"]
    print(f"  用户主观满意度: —")
    print(f"    状态: {status_map[m['status']]}")

    # 采纳率
    m = metrics["recommendation_adoption"]
    print(f"  系统推荐采纳率: —")
    print(f"    状态: {status_map[m['status']]}")

    # 伤病召回率
    m = metrics["injury_recall"]
    print(f"  伤病预警召回率: {m['value']}%" if m['value'] is not None else "  伤病预警召回率: —")
    print(f"    样本量: {m['sample_count']}, 状态: {status_map[m['status']]}")

    # 伤病误报率
    m = metrics["injury_false_alarm"]
    print(f"  伤病预警误报率: {m['value']}%" if m['value'] is not None else "  伤病预警误报率: —")
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
        round(records_with_actual / total_records * 100, 1)
        if total_records > 0
        else 0
    )

    # 伤病报告数
    injury_labels_dir = Path.home() / ".nanobot-runner" / "injury_labels"
    injury_count = (
        len(list(injury_labels_dir.glob("*.json")))
        if injury_labels_dir.exists()
        else 0
    )

    # 构建报告内容
    report = f"""# Phase C 基线测量报告

> 测量时间: {today}
> 数据范围: {data_start} ~ {data_end}
> 基线版本: v0.22.0

## 基线指标

| 指标 | 基线值 | 样本量 | 状态 |
|------|--------|--------|------|
| VDOT预测误差(MAE) | {_fmt(metrics['vdot_mae'], '%')} | {metrics['vdot_mae']['sample_count']} | {_status(metrics['vdot_mae'])} |
| 全马成绩预测误差 | {_fmt(metrics['race_marathon_error'], '秒')} | {metrics['race_marathon_error']['sample_count']} | {_status(metrics['race_marathon_error'])} |
| 用户主观满意度 | — | 0 | ⏳ 待v0.23补充 |
| 系统推荐采纳率 | — | 0 | ⏳ 待v0.23补充 |
| 伤病预警召回率 | {_fmt(metrics['injury_recall'], '%')} | {metrics['injury_recall']['sample_count']} | {_status(metrics['injury_recall'])} |
| 伤病预警误报率 | {_fmt(metrics['injury_false_alarm'], '%')} | {metrics['injury_false_alarm']['sample_count']} | {_status(metrics['injury_false_alarm'])} |

## 版本迭代目标

| 指标 | 基线值 | v0.23目标 | v0.24目标 | v0.25目标 |
|------|--------|-----------|-----------|-----------|
| VDOT预测误差(MAE) | {_fmt(metrics['vdot_mae'], '%')} | 下降≥5% | 下降≥5% | 下降≥5% |
| 全马成绩预测误差 | {_fmt(metrics['race_marathon_error'], '秒')} | 下降≥5% | 下降≥5% | 下降≥5% |
| 用户主观满意度 | — | ≥4.0/5.0 | +0.1 | +0.1 |
| 系统推荐采纳率 | — | >60% | +3% | +3% |
| 伤病预警召回率 | {_fmt(metrics['injury_recall'], '%')} | ≥75% | ≥75% | ≥75% |
| 伤病预警误报率 | {_fmt(metrics['injury_false_alarm'], '%')} | -3% | -3% | -3% |

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
```

- [ ] **Step 2: 运行脚本验证（dry-run模式）**

Run: `uv run python scripts/measure_baseline.py --dry-run`
Expected: 终端显示5项指标计算结果（3项有数据或无数据，2项标注待补充）

- [ ] **Step 3: Commit**

```bash
git add scripts/measure_baseline.py
git commit -m "feat(baseline): add baseline measurement and report generation script"
```

---

### Task 5: 端到端验证

**Files:**
- 无新增文件

- [ ] **Step 1: 运行完整流程 - 生成历史预测**

Run: `uv run python scripts/generate_historical_predictions.py --reset`
Expected: 生成约26个时间点的预测记录，回填实际值，输出统计摘要

- [ ] **Step 2: 运行完整流程 - 生成基线报告**

Run: `uv run python scripts/measure_baseline.py`
Expected: 生成 `docs/product/Phase_C_基线测量报告.md`，包含5项指标

- [ ] **Step 3: 检查报告内容**

Run: `type docs\product\Phase_C_基线测量报告.md`
Expected: Markdown格式报告，包含基线指标表、版本迭代目标表、数据质量说明

- [ ] **Step 4: Commit**

```bash
git add docs/product/Phase_C_基线测量报告.md
git commit -m "docs(baseline): add Phase C baseline measurement report"
```
