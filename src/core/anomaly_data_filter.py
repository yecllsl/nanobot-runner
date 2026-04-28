# 异常数据过滤器
# 过滤跑步数据中的异常记录

from dataclasses import dataclass

import polars as pl

from src.core.base.logger import get_logger

logger = get_logger(__name__)


@dataclass
class AnomalyFilterRule:
    """异常过滤规则"""

    field_name: str
    condition: str
    threshold: float
    action: str
    description: str


ANOMALY_FILTER_RULES: list[AnomalyFilterRule] = [
    AnomalyFilterRule(
        field_name="avg_heart_rate",
        condition="<",
        threshold=30,
        action="filter",
        description="心率过低（<30 bpm）可能是数据错误",
    ),
    AnomalyFilterRule(
        field_name="avg_heart_rate",
        condition=">",
        threshold=220,
        action="filter",
        description="心率过高（>220 bpm）可能是数据错误",
    ),
    AnomalyFilterRule(
        field_name="max_heart_rate",
        condition="<",
        threshold=50,
        action="filter",
        description="最大心率过低（<50 bpm）可能是数据错误",
    ),
    AnomalyFilterRule(
        field_name="max_heart_rate",
        condition=">",
        threshold=250,
        action="filter",
        description="最大心率过高（>250 bpm）可能是数据错误",
    ),
    AnomalyFilterRule(
        field_name="total_distance",
        condition="<",
        threshold=100,
        action="filter",
        description="距离过短（<100m）可能是无效记录",
    ),
    AnomalyFilterRule(
        field_name="total_distance",
        condition=">",
        threshold=100000,
        action="filter",
        description="距离过长（>100km）可能是数据错误",
    ),
    AnomalyFilterRule(
        field_name="total_timer_time",
        condition="<",
        threshold=60,
        action="filter",
        description="时长过短（<60s）可能是无效记录",
    ),
    AnomalyFilterRule(
        field_name="total_timer_time",
        condition=">",
        threshold=28800,
        action="filter",
        description="时长过长（>8小时）可能是数据错误",
    ),
]


class AnomalyDataFilter:
    """异常数据过滤器"""

    def __init__(self, rules: list[AnomalyFilterRule] | None = None) -> None:
        """
        初始化异常数据过滤器

        Args:
            rules: 过滤规则列表，如果为 None 则使用默认规则
        """
        self.rules = rules or ANOMALY_FILTER_RULES

    def filter_anomaly_data(
        self,
        data: pl.LazyFrame,
        strict_mode: bool = False,
    ) -> pl.LazyFrame:
        """
        过滤异常数据

        Args:
            data: 输入的 LazyFrame 数据
            strict_mode: 严格模式，如果为 True 则过滤掉任何触发规则的数据

        Returns:
            pl.LazyFrame: 过滤后的 LazyFrame

        Raises:
            ValueError: 当输入数据为空时
            RuntimeError: 当过滤失败时
        """
        try:
            if len(data.collect_schema()) == 0:
                raise ValueError("输入数据为空")

            filtered_data = data

            for rule in self.rules:
                if rule.field_name not in filtered_data.collect_schema().names():
                    continue

                if not strict_mode and not self._is_severe_rule(rule):
                    continue

                filtered_data = self._apply_filter_rule(filtered_data, rule)

            return filtered_data
        except ValueError:
            raise
        except Exception as e:
            logger.error(f"异常数据过滤失败：{e}")
            raise RuntimeError(f"异常数据过滤失败：{e}") from e

    def _is_severe_rule(self, rule: AnomalyFilterRule) -> bool:
        """判断是否为严重异常规则"""
        severe_thresholds = {
            "avg_heart_rate": [(30, "<"), (220, ">")],
            "max_heart_rate": [(50, "<"), (250, ">")],
            "total_distance": [(100, "<"), (100000, ">")],
            "total_timer_time": [(60, "<"), (28800, ">")],
        }

        if rule.field_name in severe_thresholds:
            thresholds = severe_thresholds[rule.field_name]
            return (rule.threshold, rule.condition) in thresholds

        return True

    def _apply_filter_rule(
        self, data: pl.LazyFrame, rule: AnomalyFilterRule
    ) -> pl.LazyFrame:
        """应用过滤规则"""
        if rule.action == "filter":
            if rule.condition == "<":
                return data.filter(pl.col(rule.field_name) >= rule.threshold)
            elif rule.condition == ">":
                return data.filter(pl.col(rule.field_name) <= rule.threshold)
            elif rule.condition == "<=":
                return data.filter(pl.col(rule.field_name) > rule.threshold)
            elif rule.condition == ">=":
                return data.filter(pl.col(rule.field_name) < rule.threshold)

        return data

    def get_filter_summary(self, data: pl.LazyFrame) -> dict:
        """
        获取过滤摘要

        Args:
            data: 输入的 LazyFrame 数据

        Returns:
            dict: 过滤摘要
        """
        try:
            original_count = data.collect().height
            filtered_data = self.filter_anomaly_data(data)
            filtered_count = filtered_data.collect().height

            return {
                "original_count": original_count,
                "filtered_count": filtered_count,
                "removed_count": original_count - filtered_count,
                "removal_rate": (
                    round((original_count - filtered_count) / original_count * 100, 2)
                    if original_count > 0
                    else 0.0
                ),
            }
        except Exception as e:
            logger.error(f"获取过滤摘要失败：{e}")
            return {
                "original_count": 0,
                "filtered_count": 0,
                "removed_count": 0,
                "removal_rate": 0.0,
                "error": str(e),
            }

    def add_custom_rule(self, rule: AnomalyFilterRule) -> None:
        """
        添加自定义过滤规则

        Args:
            rule: 过滤规则
        """
        self.rules.append(rule)

    def remove_rule(self, field_name: str, condition: str, threshold: float) -> bool:
        """
        移除过滤规则

        Args:
            field_name: 字段名
            condition: 条件
            threshold: 阈值

        Returns:
            bool: 是否成功移除
        """
        for i, rule in enumerate(self.rules):
            if (
                rule.field_name == field_name
                and rule.condition == condition
                and rule.threshold == threshold
            ):
                self.rules.pop(i)
                return True
        return False
