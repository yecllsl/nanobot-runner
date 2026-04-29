# 数据处理 Handler
# 负责数据导入和统计的业务逻辑调用

from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import polars as pl
from rich.progress import Progress, SpinnerColumn, TextColumn

from src.core.base.context import AppContext, AppContextFactory


class DataHandler:
    """数据处理业务逻辑"""

    def __init__(self, context: AppContext | None = None) -> None:
        """
        初始化数据处理器

        Args:
            context: 应用上下文（可选），未提供则使用全局上下文
        """
        if context is None:
            context = AppContextFactory.create()

        self.config = context.config
        self.storage = context.storage
        self.indexer = context.indexer
        self.parser = context.parser
        self.importer = context.importer
        self.session_repo = context.session_repo
        self.analytics = context.analytics

    def import_file(self, file_path: Path, force: bool = False) -> dict:
        """
        导入单个 FIT 文件

        Args:
            file_path: FIT 文件路径
            force: 是否强制导入，跳过去重

        Returns:
            dict: 导入结果
        """
        return self.importer.import_file(file_path, force=force)

    def import_directory(
        self, directory: Path, force: bool = False
    ) -> tuple[int, int, list[str]]:
        """
        导入目录中的所有 FIT 文件

        Args:
            directory: 目录路径
            force: 是否强制导入

        Returns:
            tuple: (成功数量, 跳过数量, 错误列表)
        """
        fit_files = list(directory.glob("*.fit"))
        if not fit_files:
            return 0, 0, []

        success_count = 0
        skip_count = 0
        errors = []

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            transient=True,
        ) as progress:
            progress.add_task(f"正在导入 {len(fit_files)} 个文件", total=None)

            for fit_file in fit_files:
                result = self.importer.import_file(fit_file, force=force)
                if result.get("status") == "added":
                    success_count += 1
                elif result.get("status") == "skipped":
                    skip_count += 1
                else:
                    errors.append(
                        f"{fit_file.name}: {result.get('message', '未知错误')}"
                    )

        return success_count, skip_count, errors

    def get_stats(
        self,
        year: int | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> pl.DataFrame:
        """
        获取统计数据

        Args:
            year: 指定年份
            start_date: 开始日期 (YYYY-MM-DD)
            end_date: 结束日期 (YYYY-MM-DD)

        Returns:
            pl.DataFrame: 统计数据
        """
        years = [year] if year else None
        lf = self.storage.read_parquet(years=years)
        df = lf.collect()

        if df.is_empty():
            return df

        if start_date or end_date:
            df = self._filter_by_date_range(df, start_date, end_date)

        return df

    def _filter_by_date_range(
        self, df: pl.DataFrame, start_date: str | None, end_date: str | None
    ) -> pl.DataFrame:
        """
        按日期范围过滤数据（基于会话开始时间）

        使用 session_start_time 过滤，确保跨日期边界的会话被正确归入开始日期。
        结束日期包含当天全天数据（即 < end_date + 1 day）。

        Args:
            df: 原始数据
            start_date: 开始日期
            end_date: 结束日期

        Returns:
            pl.DataFrame: 过滤后的数据
        """
        if "session_start_time" not in df.columns:
            return df

        if start_date:
            start_dt = datetime.strptime(start_date, "%Y-%m-%d")
            df = df.filter(pl.col("session_start_time") >= start_dt)

        if end_date:
            end_dt = datetime.strptime(end_date, "%Y-%m-%d") + timedelta(days=1)
            df = df.filter(pl.col("session_start_time") < end_dt)

        return df

    def get_recent_runs(self, limit: int = 10) -> list[dict[str, Any]]:
        """
        获取最近的训练记录

        Args:
            limit: 返回记录数量

        Returns:
            list[dict]: 训练记录列表
        """
        sessions = self.session_repo.get_recent_sessions(limit=limit)

        runs = []
        for session in sessions:
            vdot = None
            if session.distance_m >= 1500 and session.duration_s > 0:
                vdot = self.analytics.calculate_vdot(
                    session.distance_m, session.duration_s
                )

            runs.append(
                {
                    "timestamp": session.timestamp,
                    "distance_km": round(session.distance_km, 2),
                    "duration_min": round(session.duration_min, 1),
                    "avg_pace_sec_km": session.avg_pace_sec_km,
                    "avg_heart_rate": session.avg_heart_rate,
                    "vdot": round(vdot, 2) if vdot else None,
                }
            )

        return runs
