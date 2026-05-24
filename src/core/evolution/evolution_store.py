# 决策追踪存储层
# 使用Parquet按月分片存储DecisionLog和OutcomeRecord
# 存储结构: data_dir/decisions/YYYY-MM/decisions_YYYY-MM.parquet
#           data_dir/outcomes/YYYY-MM/outcomes_YYYY-MM.parquet
# 遵循项目核心约束: Parquet按月分片 + Polars LazyFrame查询

from __future__ import annotations

import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import polars as pl

from src.core.base.logger import get_logger
from src.core.evolution.models import (
    CalibrationProfile,
    DecisionLog,
    OutcomeRecord,
    PromptTuningParams,
)
from src.core.transparency.models import DecisionType

logger = get_logger(__name__)

_DECISIONS_PARQUET_SCHEMA = pl.Schema(
    {
        "decision_id": pl.String(),
        "timestamp": pl.String(),
        "runner_state": pl.String(),
        "decision_type": pl.String(),
        "tool_call_chain": pl.String(),
        "prediction_snapshot": pl.String(),
        "recommendation_text": pl.String(),
        "execution_status": pl.String(),
        "recommendation_accepted": pl.String(),
        "session_key": pl.String(),
        "goal_state": pl.String(),
    }
)

_OUTCOMES_PARQUET_SCHEMA = pl.Schema(
    {
        "outcome_id": pl.String(),
        "decision_id": pl.String(),
        "outcome_timestamp": pl.String(),
        "actual_vdot": pl.String(),
        "actual_injury": pl.String(),
        "execution_fidelity": pl.String(),
        "user_feedback_score": pl.String(),
        "user_feedback_text": pl.String(),
        "prediction_error": pl.String(),
        "prediction_direction": pl.String(),
        "session_id": pl.String(),
    }
)


def _decision_to_row(decision: DecisionLog) -> dict[str, str | None]:
    """将DecisionLog转换为Parquet行（JSON字符串存储复杂字段）

    Args:
        decision: 决策日志对象

    Returns:
        dict[str, str | None]: Parquet行数据
    """
    return {
        "decision_id": decision.decision_id,
        "timestamp": decision.timestamp.isoformat(),
        "runner_state": json.dumps(decision.runner_state, ensure_ascii=False),
        "decision_type": decision.decision_type.value,
        "tool_call_chain": json.dumps(decision.tool_call_chain, ensure_ascii=False),
        "prediction_snapshot": (
            json.dumps(decision.prediction_snapshot, ensure_ascii=False)
            if decision.prediction_snapshot is not None
            else None
        ),
        "recommendation_text": decision.recommendation_text,
        "execution_status": decision.execution_status,
        "recommendation_accepted": (
            str(decision.recommendation_accepted)
            if decision.recommendation_accepted is not None
            else None
        ),
        "session_key": decision.session_key,
        "goal_state": decision.goal_state,
    }


def _row_to_decision(row: dict[str, Any]) -> DecisionLog:
    """将Parquet行转换为DecisionLog对象

    Args:
        row: Parquet行数据

    Returns:
        DecisionLog: 决策日志对象
    """
    runner_state: dict[str, Any] = {}
    if row.get("runner_state"):
        runner_state = json.loads(row["runner_state"])

    tool_call_chain: list[dict[str, Any]] = []
    if row.get("tool_call_chain"):
        tool_call_chain = json.loads(row["tool_call_chain"])

    prediction_snapshot: dict[str, Any] | None = None
    if row.get("prediction_snapshot"):
        prediction_snapshot = json.loads(row["prediction_snapshot"])

    recommendation_accepted: bool | None = None
    if row.get("recommendation_accepted") is not None:
        val = row["recommendation_accepted"]
        if isinstance(val, str):
            recommendation_accepted = val.lower() == "true"
        elif isinstance(val, bool):
            recommendation_accepted = val

    return DecisionLog(
        decision_id=row["decision_id"],
        timestamp=datetime.fromisoformat(row["timestamp"]),
        runner_state=runner_state,
        decision_type=DecisionType(row["decision_type"]),
        tool_call_chain=tool_call_chain,
        prediction_snapshot=prediction_snapshot,
        recommendation_text=row.get("recommendation_text"),
        execution_status=row["execution_status"],
        recommendation_accepted=recommendation_accepted,
        session_key=row.get("session_key", ""),
        goal_state=row.get("goal_state"),
    )


def _outcome_to_row(outcome: OutcomeRecord) -> dict[str, str | None]:
    """将OutcomeRecord转换为Parquet行

    Args:
        outcome: 结果记录对象

    Returns:
        dict[str, str | None]: Parquet行数据
    """
    return {
        "outcome_id": outcome.outcome_id,
        "decision_id": outcome.decision_id,
        "outcome_timestamp": outcome.outcome_timestamp.isoformat(),
        "actual_vdot": str(outcome.actual_vdot)
        if outcome.actual_vdot is not None
        else None,
        "actual_injury": str(outcome.actual_injury),
        "execution_fidelity": (
            str(outcome.execution_fidelity)
            if outcome.execution_fidelity is not None
            else None
        ),
        "user_feedback_score": (
            str(outcome.user_feedback_score)
            if outcome.user_feedback_score is not None
            else None
        ),
        "user_feedback_text": outcome.user_feedback_text,
        "prediction_error": (
            str(outcome.prediction_error)
            if outcome.prediction_error is not None
            else None
        ),
        "prediction_direction": outcome.prediction_direction,
        "session_id": outcome.session_id,
    }


def _row_to_outcome(row: dict[str, Any]) -> OutcomeRecord:
    """将Parquet行转换为OutcomeRecord对象

    Args:
        row: Parquet行数据

    Returns:
        OutcomeRecord: 结果记录对象
    """
    actual_vdot: float | None = None
    if row.get("actual_vdot") is not None:
        actual_vdot = float(row["actual_vdot"])

    actual_injury = False
    if row.get("actual_injury") is not None:
        val = row["actual_injury"]
        actual_injury = val if isinstance(val, bool) else str(val).lower() == "true"

    execution_fidelity: float | None = None
    if row.get("execution_fidelity") is not None:
        execution_fidelity = float(row["execution_fidelity"])

    user_feedback_score: int | None = None
    if row.get("user_feedback_score") is not None:
        user_feedback_score = int(float(row["user_feedback_score"]))

    prediction_error: float | None = None
    if row.get("prediction_error") is not None:
        prediction_error = float(row["prediction_error"])

    return OutcomeRecord(
        outcome_id=row["outcome_id"],
        decision_id=row["decision_id"],
        outcome_timestamp=datetime.fromisoformat(row["outcome_timestamp"]),
        actual_vdot=actual_vdot,
        actual_injury=actual_injury,
        execution_fidelity=execution_fidelity,
        user_feedback_score=user_feedback_score,
        user_feedback_text=row.get("user_feedback_text"),
        prediction_error=prediction_error,
        prediction_direction=row.get("prediction_direction"),
        session_id=row.get("session_id"),
    )


class EvolutionStore:
    """决策追踪存储层

    使用Parquet按月分片存储决策日志和结果记录。
    遵循项目核心约束: Parquet按月分片 + Polars LazyFrame查询优先。

    存储目录结构:
        data_dir/
            decisions/
                2026-05/
                    decisions_2026-05.parquet
            outcomes/
                2026-05/
                    outcomes_2026-05.parquet

    Attributes:
        data_dir: 数据根目录
    """

    def __init__(self, data_dir: Path) -> None:
        """初始化存储层

        Args:
            data_dir: 数据根目录
        """
        self._data_dir = data_dir
        self._decisions_dir = data_dir / "decisions"
        self._outcomes_dir = data_dir / "outcomes"
        self._calibrations_dir = data_dir / "calibrations"
        self._tuning_dir = data_dir / "tuning"

    @property
    def data_dir(self) -> Path:
        """数据根目录（只读）"""
        return self._data_dir

    def _get_decisions_file_path(self, timestamp: datetime) -> Path:
        """获取决策日志Parquet文件路径（按月分片）

        路径格式: data_dir/decisions/YYYY-MM/decisions_YYYY-MM.parquet

        Args:
            timestamp: 时间戳，用于确定分片文件

        Returns:
            Path: 对应年月的Parquet文件路径
        """
        year_month = f"{timestamp.year}-{timestamp.month:02d}"
        return self._decisions_dir / year_month / f"decisions_{year_month}.parquet"

    def _get_outcomes_file_path(self, timestamp: datetime) -> Path:
        """获取结果记录Parquet文件路径（按月分片）

        路径格式: data_dir/outcomes/YYYY-MM/outcomes_YYYY-MM.parquet

        Args:
            timestamp: 时间戳，用于确定分片文件

        Returns:
            Path: 对应年月的Parquet文件路径
        """
        year_month = f"{timestamp.year}-{timestamp.month:02d}"
        return self._outcomes_dir / year_month / f"outcomes_{year_month}.parquet"

    def _append_to_parquet(
        self, file_path: Path, row: dict[str, Any], schema: pl.Schema
    ) -> None:
        """追加一行数据到Parquet文件（原子写入）

        若文件不存在则创建，存在则读取后追加写入。
        使用临时文件+os.replace确保原子性。

        Args:
            file_path: Parquet文件路径
            row: 行数据字典
            schema: Parquet Schema
        """
        file_path.parent.mkdir(parents=True, exist_ok=True)
        new_df = pl.DataFrame([row], schema=schema)

        if file_path.exists():
            existing_df = pl.read_parquet(file_path)
            combined = pl.concat([existing_df, new_df], how="vertical_relaxed")
        else:
            combined = new_df

        # 原子写入: 先写临时文件，再替换
        tmp_path = file_path.with_suffix(".parquet.tmp")
        try:
            combined.write_parquet(tmp_path, compression="snappy")
            tmp_path.replace(file_path)
        except Exception:
            if tmp_path.exists():
                tmp_path.unlink()
            raise

    def save_decision(self, decision: DecisionLog) -> None:
        """保存决策日志，追加写入Parquet文件

        自动创建所需的目录结构。使用原子写入确保数据安全。

        Args:
            decision: 决策日志对象
        """
        file_path = self._get_decisions_file_path(decision.timestamp)
        row = _decision_to_row(decision)
        self._append_to_parquet(file_path, row, _DECISIONS_PARQUET_SCHEMA)

    def save_outcome(self, outcome: OutcomeRecord) -> None:
        """保存结果记录，追加写入Parquet文件

        自动创建所需的目录结构。使用原子写入确保数据安全。

        Args:
            outcome: 结果记录对象
        """
        file_path = self._get_outcomes_file_path(outcome.outcome_timestamp)
        row = _outcome_to_row(outcome)
        self._append_to_parquet(file_path, row, _OUTCOMES_PARQUET_SCHEMA)

    def _scan_decisions(
        self,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> pl.LazyFrame:
        """使用LazyFrame扫描决策日志Parquet文件

        根据日期范围确定需要扫描的月份分片，避免全量加载。
        无日期范围时扫描全部分片。

        Args:
            start_date: 起始日期（可选）
            end_date: 结束日期（可选）

        Returns:
            pl.LazyFrame: 决策日志LazyFrame
        """
        if not self._decisions_dir.exists():
            return pl.DataFrame(schema=_DECISIONS_PARQUET_SCHEMA).lazy()

        parquet_files = self._get_parquet_files_in_range(
            self._decisions_dir, start_date, end_date
        )

        if not parquet_files:
            return pl.DataFrame(schema=_DECISIONS_PARQUET_SCHEMA).lazy()

        return pl.scan_parquet(parquet_files)

    def _scan_outcomes(
        self,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> pl.LazyFrame:
        """使用LazyFrame扫描结果记录Parquet文件

        根据日期范围确定需要扫描的月份分片，避免全量加载。

        Args:
            start_date: 起始日期（可选）
            end_date: 结束日期（可选）

        Returns:
            pl.LazyFrame: 结果记录LazyFrame
        """
        if not self._outcomes_dir.exists():
            return pl.DataFrame(schema=_OUTCOMES_PARQUET_SCHEMA).lazy()

        parquet_files = self._get_parquet_files_in_range(
            self._outcomes_dir, start_date, end_date
        )

        if not parquet_files:
            return pl.DataFrame(schema=_OUTCOMES_PARQUET_SCHEMA).lazy()

        return pl.scan_parquet(parquet_files)

    def _get_parquet_files_in_range(
        self,
        base_dir: Path,
        start_date: datetime | None,
        end_date: datetime | None,
    ) -> list[Path]:
        """获取日期范围内的Parquet文件列表

        根据目录名(YYYY-MM格式)与日期范围比较，过滤需要扫描的分片。

        Args:
            base_dir: 基础目录（decisions/或outcomes/）
            start_date: 起始日期（可选）
            end_date: 结束日期（可选）

        Returns:
            list[Path]: 需要扫描的Parquet文件路径列表
        """
        if not base_dir.exists():
            return []

        all_files = sorted(base_dir.rglob("*.parquet"))
        if start_date is None and end_date is None:
            return all_files

        filtered: list[Path] = []
        for f in all_files:
            # 从路径提取YYYY-MM: .../2026-05/decisions_2026-05.parquet
            parts = f.parts
            year_month_str = None
            for part in parts:
                if len(part) == 7 and part[4] == "-" and part[:4].isdigit():
                    year_month_str = part
                    break

            if year_month_str is None:
                continue

            try:
                year, month = int(year_month_str[:4]), int(year_month_str[5:7])
                file_start = datetime(year, month, 1)
                # 月份结束时间
                if month == 12:
                    file_end = datetime(year + 1, 1, 1)
                else:
                    file_end = datetime(year, month + 1, 1)

                # 文件月份范围与查询范围有交集
                if start_date is not None and file_end <= start_date:
                    continue
                if end_date is not None and file_start > end_date:
                    continue
                filtered.append(f)
            except (ValueError, IndexError):
                continue

        return filtered

    def query_decisions(
        self,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        decision_type: DecisionType | None = None,
        execution_status: str | None = None,
        limit: int = 100,
    ) -> list[DecisionLog]:
        """按条件查询决策日志，按时间倒序返回

        使用LazyFrame管道: scan → filter → sort → limit → collect

        Args:
            start_date: 起始日期（可选）
            end_date: 结束日期（可选）
            decision_type: 决策类型过滤（可选）
            execution_status: 执行状态过滤（可选）
            limit: 返回数量限制，默认100

        Returns:
            list[DecisionLog]: 符合条件的决策日志列表，按时间倒序
        """
        lf = self._scan_decisions(start_date, end_date)

        filters: list[pl.Expr] = []
        if start_date is not None:
            filters.append(pl.col("timestamp") >= start_date.isoformat())
        if end_date is not None:
            filters.append(pl.col("timestamp") <= end_date.isoformat())
        if decision_type is not None:
            filters.append(pl.col("decision_type") == decision_type.value)
        if execution_status is not None:
            filters.append(pl.col("execution_status") == execution_status)

        if filters:
            lf = lf.filter(pl.all_horizontal(filters))

        lf = lf.sort("timestamp", descending=True).head(limit)
        df = lf.collect()

        return [_row_to_decision(row) for row in df.iter_rows(named=True)]

    def query_outcomes(
        self,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        decision_id: str | None = None,
        limit: int = 100,
    ) -> list[OutcomeRecord]:
        """按条件查询结果记录，按时间倒序返回

        使用LazyFrame管道: scan → filter → sort → limit → collect

        Args:
            start_date: 起始日期（可选），基于outcome_timestamp
            end_date: 结束日期（可选），基于outcome_timestamp
            decision_id: 关联的决策ID过滤（可选）
            limit: 返回数量限制，默认100

        Returns:
            list[OutcomeRecord]: 符合条件的结果记录列表，按时间倒序
        """
        lf = self._scan_outcomes(start_date, end_date)

        filters: list[pl.Expr] = []
        if start_date is not None:
            filters.append(pl.col("outcome_timestamp") >= start_date.isoformat())
        if end_date is not None:
            filters.append(pl.col("outcome_timestamp") <= end_date.isoformat())
        if decision_id is not None:
            filters.append(pl.col("decision_id") == decision_id)

        if filters:
            lf = lf.filter(pl.all_horizontal(filters))

        lf = lf.sort("outcome_timestamp", descending=True).head(limit)
        df = lf.collect()

        return [_row_to_outcome(row) for row in df.iter_rows(named=True)]

    def get_decision_by_id(self, decision_id: str) -> DecisionLog | None:
        """根据决策ID获取决策日志

        使用LazyFrame按decision_id过滤，仅collect匹配行。

        Args:
            decision_id: 决策唯一标识

        Returns:
            DecisionLog | None: 决策日志对象，未找到返回None
        """
        if not self._decisions_dir.exists():
            return None

        parquet_files = sorted(self._decisions_dir.rglob("*.parquet"))
        if not parquet_files:
            return None

        lf = pl.scan_parquet(parquet_files)
        lf = lf.filter(pl.col("decision_id") == decision_id)
        df = lf.collect()

        if df.is_empty():
            return None

        return _row_to_decision(df.row(0, named=True))

    def update_decision(self, decision: DecisionLog) -> bool:
        """更新决策日志（原子写入）

        读取对应月份的Parquet文件，替换匹配decision_id的行，
        使用临时文件+os.replace确保原子性。

        Args:
            decision: 更新后的决策日志对象

        Returns:
            bool: 更新成功返回True，文件不存在返回False
        """
        file_path = self._get_decisions_file_path(decision.timestamp)
        if not file_path.exists():
            logger.warning("更新决策失败: 文件不存在, path=%s", file_path)
            return False

        existing_df = pl.read_parquet(file_path)
        new_row = pl.DataFrame(
            [_decision_to_row(decision)], schema=_DECISIONS_PARQUET_SCHEMA
        )

        # 替换匹配行
        mask = existing_df["decision_id"] != decision.decision_id
        filtered_df = existing_df.filter(mask)
        combined = pl.concat([filtered_df, new_row], how="vertical_relaxed")

        # 原子写入
        tmp_path = file_path.with_suffix(".parquet.tmp")
        try:
            combined.write_parquet(tmp_path, compression="snappy")
            tmp_path.replace(file_path)
        except Exception:
            if tmp_path.exists():
                tmp_path.unlink()
            raise

        return True

    def get_decision_outcome_pairs(
        self,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        days: int = 90,
    ) -> list[tuple[DecisionLog, OutcomeRecord]]:
        """获取决策-结果配对列表

        根据decision_id关联DecisionLog和OutcomeRecord，
        仅返回有对应结果的决策记录。

        Args:
            start_date: 起始日期（可选），基于决策的timestamp
            end_date: 结束日期（可选），基于决策的timestamp
            days: 查询天数范围（默认90天），仅当start_date为None时生效

        Returns:
            list[tuple[DecisionLog, OutcomeRecord]]: 决策-结果配对列表
        """
        # v0.25: days参数限制查询范围
        if start_date is None and days > 0:
            start_date = datetime.now() - timedelta(days=days)
        decisions_lf = self._scan_decisions(start_date, end_date)

        if start_date is not None:
            decisions_lf = decisions_lf.filter(
                pl.col("timestamp") >= start_date.isoformat()
            )
        if end_date is not None:
            decisions_lf = decisions_lf.filter(
                pl.col("timestamp") <= end_date.isoformat()
            )

        decisions_df = decisions_lf.collect()
        outcomes_df = self._scan_outcomes().collect()

        if decisions_df.is_empty() or outcomes_df.is_empty():
            return []

        # 构建decision_id -> OutcomeRecord映射（保留最新的）
        outcome_map: dict[str, OutcomeRecord] = {}
        for row in outcomes_df.iter_rows(named=True):
            outcome = _row_to_outcome(row)
            if (
                outcome.decision_id not in outcome_map
                or outcome.outcome_timestamp
                > outcome_map[outcome.decision_id].outcome_timestamp
            ):
                outcome_map[outcome.decision_id] = outcome

        # 构建配对列表
        pairs: list[tuple[DecisionLog, OutcomeRecord]] = []
        for row in decisions_df.iter_rows(named=True):
            decision = _row_to_decision(row)
            if decision.decision_id in outcome_map:
                pairs.append((decision, outcome_map[decision.decision_id]))

        # 按决策时间倒序排列
        pairs.sort(key=lambda x: x[0].timestamp, reverse=True)

        return pairs

    def save_calibration_profile(self, profile: CalibrationProfile) -> None:
        """保存校准配置到JSON文件

        使用原子写入确保数据安全。

        Args:
            profile: 校准配置对象
        """
        self._calibrations_dir.mkdir(parents=True, exist_ok=True)
        file_path = self._calibrations_dir / f"{profile.model_type}_calibration.json"
        tmp_path = file_path.with_suffix(".json.tmp")
        try:
            tmp_path.write_text(
                json.dumps(profile.to_dict(), ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            tmp_path.replace(file_path)
        except Exception:
            if tmp_path.exists():
                tmp_path.unlink()
            raise

    def load_calibration_profile(self, model_type: str) -> CalibrationProfile | None:
        """从JSON文件加载校准配置

        Args:
            model_type: 模型类型（vdot/injury/training_response）

        Returns:
            CalibrationProfile | None: 校准配置对象，未找到返回None
        """
        file_path = self._calibrations_dir / f"{model_type}_calibration.json"
        if not file_path.exists():
            return None
        data = json.loads(file_path.read_text(encoding="utf-8"))
        return CalibrationProfile.from_dict(data)

    def get_prediction_actual_pairs(
        self, model_type: str, min_count: int = 10, days: int = 90
    ) -> list[tuple[float, float]]:
        """从DecisionLog/OutcomeRecord提取预测-实际配对

        按model_type从prediction_snapshot提取predicted值，从OutcomeRecord提取actual值。
        配对数 < min_count时返回空列表。

        Args:
            model_type: 模型类型（vdot/injury/training_response）
            min_count: 最小配对数阈值，低于此值返回空列表
            days: 查询天数范围（默认90天），传递给get_decision_outcome_pairs

        Returns:
            list[tuple[float, float]]: (预测值, 实际值)配对列表
        """
        all_pairs = self.get_decision_outcome_pairs(days=days)
        result: list[tuple[float, float]] = []
        prediction_keys: dict[str, str] = {
            "vdot": "predicted_vdot",
            "injury": "injury_risk_probability",
            "training_response": "predicted_vdot_impact",
        }
        pred_key = prediction_keys.get(model_type)
        if pred_key is None:
            return []
        for decision, outcome in all_pairs:
            if decision.prediction_snapshot is None:
                continue
            predicted = decision.prediction_snapshot.get(pred_key)
            if predicted is None:
                continue
            actual: float | None = None
            if model_type == "vdot":
                actual = outcome.actual_vdot
            elif model_type == "injury":
                actual = float(outcome.actual_injury)
            elif model_type == "training_response" and outcome.actual_vdot is not None:
                actual = outcome.actual_vdot - decision.runner_state.get("vdot", 0)
            if actual is None:
                continue
            result.append((float(predicted), actual))
        if len(result) < min_count:
            return []
        return result

    def save_model_params(self, model_type: str, params: dict[str, Any]) -> None:
        """保存模型参数到JSON文件

        使用原子写入确保数据安全。

        Args:
            model_type: 模型类型
            params: 模型参数字典
        """
        self._calibrations_dir.mkdir(parents=True, exist_ok=True)
        file_path = self._calibrations_dir / f"{model_type}_params.json"
        tmp_path = file_path.with_suffix(".json.tmp")
        try:
            tmp_path.write_text(
                json.dumps(params, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            tmp_path.replace(file_path)
        except Exception:
            if tmp_path.exists():
                tmp_path.unlink()
            raise

    def load_model_params(self, model_type: str) -> dict[str, Any] | None:
        """从JSON文件加载模型参数

        Args:
            model_type: 模型类型

        Returns:
            dict[str, Any] | None: 模型参数字典，未找到返回None
        """
        file_path = self._calibrations_dir / f"{model_type}_params.json"
        if not file_path.exists():
            return None
        return json.loads(file_path.read_text(encoding="utf-8"))

    # ---- v0.25 新增方法 ----

    def save_prompt_tuning_params(self, params: PromptTuningParams) -> None:
        """保存提示调优参数到JSON文件

        使用原子写入确保数据安全。

        Args:
            params: 提示调优参数对象
        """
        self._tuning_dir.mkdir(parents=True, exist_ok=True)
        file_path = self._tuning_dir / "prompt_params.json"
        tmp_path = file_path.with_suffix(".json.tmp")
        try:
            tmp_path.write_text(
                json.dumps(params.to_dict(), ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            tmp_path.replace(file_path)
        except Exception:
            if tmp_path.exists():
                tmp_path.unlink()
            raise

    def load_prompt_tuning_params(self) -> PromptTuningParams | None:
        """从JSON文件加载提示调优参数

        Returns:
            PromptTuningParams | None: 提示调优参数对象，文件不存在或损坏返回None
        """
        file_path = self._tuning_dir / "prompt_params.json"
        if not file_path.exists():
            return None
        try:
            data = json.loads(file_path.read_text(encoding="utf-8"))
            return PromptTuningParams.from_dict(data)
        except Exception:
            logger.warning("提示调优参数文件损坏，返回None")
            return None

    def save_trigger_state(self, key: str, value: Any) -> None:
        """保存触发器状态到JSON文件

        合并写入：读取已有状态，更新指定key后原子写入。

        Args:
            key: 触发器状态键
            value: 触发器状态值
        """
        self._tuning_dir.mkdir(parents=True, exist_ok=True)
        file_path = self._tuning_dir / "trigger_state.json"
        state: dict[str, Any] = {}
        if file_path.exists():
            try:
                state = json.loads(file_path.read_text(encoding="utf-8"))
            except Exception:
                state = {}
        state[key] = value
        tmp_path = file_path.with_suffix(".json.tmp")
        try:
            tmp_path.write_text(
                json.dumps(state, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            tmp_path.replace(file_path)
        except Exception:
            if tmp_path.exists():
                tmp_path.unlink()
            raise

    def load_trigger_state(self, key: str) -> Any | None:
        """加载触发器状态

        Args:
            key: 触发器状态键

        Returns:
            Any | None: 触发器状态值，键不存在或文件不存在返回None
        """
        file_path = self._tuning_dir / "trigger_state.json"
        if not file_path.exists():
            return None
        try:
            state = json.loads(file_path.read_text(encoding="utf-8"))
            return state.get(key)
        except Exception:
            return None

    def count_decisions(self) -> int:
        """轻量计数决策记录总数

        使用LazyFrame扫描Parquet文件，仅计算行数而不加载全部数据。

        Returns:
            int: 决策记录总数
        """
        decisions_dir = self._data_dir / "decisions"
        if not decisions_dir.exists():
            return 0
        total = 0
        for month_dir in sorted(decisions_dir.iterdir()):
            if not month_dir.is_dir():
                continue
            for parquet_file in month_dir.glob("*.parquet"):
                try:
                    lf = pl.scan_parquet(parquet_file)
                    total += lf.select(pl.len()).collect().item()
                except Exception:
                    continue
        return total
