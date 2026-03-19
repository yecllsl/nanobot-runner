# 训练回顾报告生成模块
# 支持周报、月报、训练周期报告等多种报告类型

from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

import polars as pl

from src.core.analytics import AnalyticsEngine
from src.core.config import ConfigManager
from src.core.logger import get_logger
from src.core.storage import StorageManager

logger = get_logger(__name__)


class ReportType(Enum):
    """报告类型枚举"""

    WEEKLY = "weekly"  # 周报
    MONTHLY = "monthly"  # 月报
    TRAINING_CYCLE = "training_cycle"  # 训练周期报告


@dataclass
class ReportConfig:
    """报告配置数据类"""

    report_type: ReportType
    start_date: datetime
    end_date: datetime
    age: int = 30  # 年龄，用于计算最大心率
    rest_hr: int = 60  # 静息心率
    include_hr_analysis: bool = True  # 是否包含心率分析
    include_vdot_trend: bool = True  # 是否包含 VDOT 趋势
    include_training_load: bool = True  # 是否包含训练负荷


class TemplateEngine:
    """报告模板引擎

    支持自定义模板，使用 Python 字符串格式化语法
    模板变量使用 {variable_name} 语法
    """

    def __init__(self, template_path: Optional[Path] = None) -> None:
        """
        初始化模板引擎

        Args:
            template_path: 自定义模板文件路径（可选）
        """
        self.template_path = template_path
        self._templates: Dict[str, str] = {}
        self._load_default_templates()

    def _load_default_templates(self) -> None:
        """加载默认模板"""
        # 周报模板
        self._templates[
            "weekly"
        ] = """# 跑步训练周报

**报告周期**: {start_date} 至 {end_date}
**生成时间**: {generated_at}

## 训练摘要

- **训练次数**: {total_runs} 次
- **总距离**: {total_distance:.2f} km
- **总时长**: {total_duration:.2f} 小时
- **平均配速**: {avg_pace}
- **平均心率**: {avg_hr:.1f} bpm

## 训练负荷

- **ATL (疲劳)**: {atl:.2f}
- **CTL (体能)**: {ctl:.2f}
- **TSB (状态)**: {tsb:.2f}
- **体能状态**: {fitness_status}

## 心率区间分布

{hr_zones}

## VDOT 趋势

{vdot_trend}

## 训练建议

{training_advice}
"""

        # 月报模板
        self._templates[
            "monthly"
        ] = """# 跑步训练月报

**报告周期**: {start_date} 至 {end_date}
**生成时间**: {generated_at}

## 月度训练摘要

- **训练次数**: {total_runs} 次
- **总距离**: {total_distance:.2f} km
- **总时长**: {total_duration:.2f} 小时
- **平均配速**: {avg_pace}
- **平均心率**: {avg_hr:.1f} bpm
- **总 TSS**: {total_tss:.0f}

## 体能变化

- **月初 CTL**: {start_ctl:.2f}
- **月末 CTL**: {end_ctl:.2f}
- **CTL 变化**: {ctl_change:+.2f}
- **月末 ATL**: {atl:.2f}
- **月末 TSB**: {tsb:.2f}
- **体能状态**: {fitness_status}

## 心率区间分布

{hr_zones}

## 配速分布

{pace_distribution}

## VDOT 趋势

{vdot_trend}

## 月度总结与建议

{training_advice}
"""

        # 训练周期报告模板
        self._templates[
            "training_cycle"
        ] = """# 训练周期报告

**报告周期**: {start_date} 至 {end_date}
**周期类型**: {cycle_type}
**生成时间**: {generated_at}

## 周期训练摘要

- **训练次数**: {total_runs} 次
- **总距离**: {total_distance:.2f} km
- **总时长**: {total_duration:.2f} 小时
- **平均配速**: {avg_pace}
- **平均心率**: {avg_hr:.1f} bpm
- **总 TSS**: {total_tss:.0f}
- **平均 TSS/周**: {avg_weekly_tss:.0f}

## 训练负荷趋势

- **周期初 ATL**: {start_atl:.2f}
- **周期末 ATL**: {end_atl:.2f}
- **周期初 CTL**: {start_ctl:.2f}
- **周期末 CTL**: {end_ctl:.2f}
- **CTL 变化**: {ctl_change:+.2f}
- **周期末 TSB**: {tsb:.2f}
- **体能状态**: {fitness_status}

## 心率区间分布

{hr_zones}

## 配速分布

{pace_distribution}

## VDOT 变化

{vdot_trend}

## 周期评估

{cycle_evaluation}

## 下一周期建议

{next_cycle_advice}
"""

    def get_template(self, report_type: ReportType) -> str:
        """
        获取指定报告类型的模板

        Args:
            report_type: 报告类型

        Returns:
            str: 模板字符串
        """
        # 如果提供了自定义模板文件，优先使用
        if self.template_path and self.template_path.exists():
            try:
                return self.template_path.read_text(encoding="utf-8")
            except Exception as e:
                logger.warning(f"读取自定义模板失败，使用默认模板：{e}")

        # 使用内置模板
        template_key = report_type.value
        return self._templates.get(template_key, self._templates["weekly"])  # 默认返回周报模板

    def render(self, template: str, variables: Dict[str, Any]) -> str:
        """
        渲染模板

        Args:
            template: 模板字符串
            variables: 模板变量字典

        Returns:
            str: 渲染后的文本
        """
        try:
            # 使用 Python 字符串格式化
            return template.format(**variables)
        except KeyError as e:
            logger.warning(f"模板变量缺失：{e}")
            # 保留未替换的变量标记
            return template
        except Exception as e:
            logger.error(f"模板渲染失败：{e}")
            return f"模板渲染失败：{e}"

    def set_custom_template(
        self, report_type: ReportType, template_content: str
    ) -> None:
        """
        设置自定义模板

        Args:
            report_type: 报告类型
            template_content: 模板内容
        """
        self._templates[report_type.value] = template_content
        logger.debug(f"已设置自定义模板：{report_type.value}")


class ReportGenerator:
    """报告生成器

    负责生成各种类型的训练回顾报告
    """

    def __init__(
        self,
        config: Optional[ConfigManager] = None,
        storage: Optional[StorageManager] = None,
        analytics: Optional[AnalyticsEngine] = None,
        template_engine: Optional[TemplateEngine] = None,
    ) -> None:
        """
        初始化报告生成器

        Args:
            config: 配置管理器（可选）
            storage: 存储管理器（可选）
            analytics: 分析引擎（可选）
            template_engine: 模板引擎（可选）
        """
        self.config = config or ConfigManager()
        self.storage = storage or StorageManager(self.config.data_dir)
        self.analytics = analytics or AnalyticsEngine(self.storage)
        self.template_engine = template_engine or TemplateEngine()

    def generate_report(
        self,
        report_type: ReportType,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        age: int = 30,
        rest_hr: int = 60,
        template_path: Optional[Path] = None,
    ) -> Dict[str, Any]:
        """
        生成训练回顾报告

        Args:
            report_type: 报告类型
            start_date: 开始日期（不指定则自动计算）
            end_date: 结束日期（不指定则使用今天）
            age: 年龄（用于计算最大心率）
            rest_hr: 静息心率
            template_path: 自定义模板路径（可选）

        Returns:
            Dict[str, Any]: 报告数据，包含：
                - success: 是否成功
                - report_type: 报告类型
                - content: 报告内容（Markdown 格式）
                - data: 原始数据字典
                - message: 提示信息
                - error: 错误信息（失败时）

        Raises:
            ValueError: 当日期范围无效时
        """
        try:
            # 确定日期范围
            end_dt = end_date or datetime.now()
            start_dt = self._calculate_start_date(report_type, end_dt, start_date)

            # 验证日期范围
            if start_dt > end_dt:
                raise ValueError("开始日期不能晚于结束日期")

            # 创建报告配置
            config = ReportConfig(
                report_type=report_type,
                start_date=start_dt,
                end_date=end_dt,
                age=age,
                rest_hr=rest_hr,
            )

            # 收集报告数据
            report_data = self._collect_report_data(config)

            # 生成报告内容
            content = self._generate_report_content(
                report_type, report_data, template_path
            )

            # 构建返回结果
            result = {
                "success": True,
                "report_type": report_type.value,
                "content": content,
                "data": report_data,
                "message": f"{self._get_report_type_name(report_type)}生成成功",
                "generated_at": datetime.now().isoformat(),
            }

            logger.info(f"报告生成成功：{report_type.value}")
            return result

        except ValueError as e:
            logger.error(f"报告生成失败（参数错误）: {e}")
            return {
                "success": False,
                "error": f"参数错误：{e}",
                "report_type": report_type.value if report_type else None,
            }
        except Exception as e:
            logger.error(f"报告生成失败：{e}")
            return {
                "success": False,
                "error": f"生成失败：{e}",
                "report_type": report_type.value if report_type else None,
            }

    def _calculate_start_date(
        self,
        report_type: ReportType,
        end_date: datetime,
        start_date: Optional[datetime] = None,
    ) -> datetime:
        """
        计算报告开始日期

        Args:
            report_type: 报告类型
            end_date: 结束日期
            start_date: 指定的开始日期（可选）

        Returns:
            datetime: 开始日期
        """
        if start_date:
            return start_date

        if report_type == ReportType.WEEKLY:
            # 周报：最近 7 天
            return end_date - timedelta(days=6)
        elif report_type == ReportType.MONTHLY:
            # 月报：最近 30 天
            return end_date - timedelta(days=29)
        elif report_type == ReportType.TRAINING_CYCLE:
            # 训练周期：默认最近 42 天（一个完整训练周期）
            return end_date - timedelta(days=41)
        else:
            # 默认 7 天
            return end_date - timedelta(days=6)

    def _collect_report_data(self, config: ReportConfig) -> Dict[str, Any]:
        """
        收集报告数据

        Args:
            config: 报告配置

        Returns:
            Dict[str, Any]: 报告数据字典
        """
        start_str = config.start_date.strftime("%Y-%m-%d")
        end_str = config.end_date.strftime("%Y-%m-%d")

        # 获取基础统计数据
        stats = self.analytics.get_running_summary(
            start_date=start_str, end_date=end_str
        )

        # 处理空数据情况
        if stats.is_empty():
            return self._create_empty_report_data(config)

        # 提取统计数据
        total_runs = int(stats["total_runs"][0])
        total_distance = (
            float(stats["total_distance"][0]) if stats["total_distance"][0] else 0.0
        )
        total_duration = (
            float(stats["total_timer_time"][0]) if stats["total_timer_time"][0] else 0.0
        )
        avg_hr = (
            float(stats["avg_heart_rate"][0]) if stats["avg_heart_rate"][0] else 0.0
        )

        # 计算平均配速
        avg_pace = self._calculate_pace(total_distance, total_duration)

        # 获取训练负荷数据
        training_load = {}
        if config.include_training_load:
            training_load = self.analytics.get_training_load(days=42)

        # 获取心率区间分布
        hr_zones_data = {}
        if config.include_hr_analysis:
            hr_zones_data = self.analytics.get_heart_rate_zones(
                age=config.age, start_date=start_str, end_date=end_str
            )

        # 获取 VDOT 趋势
        vdot_trend_data = []
        if config.include_vdot_trend:
            days = (config.end_date - config.start_date).days + 1
            vdot_trend_data = self.analytics.get_vdot_trend(days=days)

        # 计算总 TSS
        total_tss = self._calculate_total_tss(config)

        # 获取训练负荷趋势（用于周期报告）
        training_load_trend = {}
        if config.report_type == ReportType.TRAINING_CYCLE:
            training_load_trend = self.analytics.get_training_load_trend(
                start_date=start_str, end_date=end_str
            )

        # 构建报告数据
        report_data = {
            # 基础信息
            "start_date": config.start_date.strftime("%Y-%m-%d"),
            "end_date": config.end_date.strftime("%Y-%m-%d"),
            "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            # 训练统计
            "total_runs": total_runs,
            "total_distance": total_distance / 1000,  # 转换为公里
            "total_duration": total_duration / 3600,  # 转换为小时
            "avg_pace": avg_pace,
            "avg_hr": avg_hr,
            "total_tss": total_tss,
            # 训练负荷
            "atl": training_load.get("atl", 0.0),
            "ctl": training_load.get("ctl", 0.0),
            "tsb": training_load.get("tsb", 0.0),
            "fitness_status": training_load.get("fitness_status", "数据不足"),
            "training_advice": training_load.get("training_advice", "暂无建议"),
            # 心率分析
            "hr_zones": hr_zones_data,
            # VDOT 趋势
            "vdot_trend": vdot_trend_data,
            # 训练负荷趋势（周期报告专用）
            "training_load_trend": training_load_trend,
            # 配速分布
            "pace_distribution": self.analytics.get_pace_distribution(),
        }

        return report_data

    def _create_empty_report_data(self, config: ReportConfig) -> Dict[str, Any]:
        """
        创建空数据报告

        Args:
            config: 报告配置

        Returns:
            Dict[str, Any]: 空报告数据
        """
        return {
            "start_date": config.start_date.strftime("%Y-%m-%d"),
            "end_date": config.end_date.strftime("%Y-%m-%d"),
            "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "total_runs": 0,
            "total_distance": 0.0,
            "total_duration": 0.0,
            "avg_pace": "0:00",
            "avg_hr": 0.0,
            "total_tss": 0.0,
            "atl": 0.0,
            "ctl": 0.0,
            "tsb": 0.0,
            "fitness_status": "数据不足",
            "training_advice": "暂无跑步数据，请先导入 FIT 文件",
            "hr_zones": {},
            "vdot_trend": [],
            "training_load_trend": {},
            "pace_distribution": {},
            "message": "暂无跑步数据，请先导入 FIT 文件",
        }

    def _calculate_pace(self, distance_m: float, duration_s: float) -> str:
        """
        计算平均配速

        Args:
            distance_m: 距离（米）
            duration_s: 时长（秒）

        Returns:
            str: 配速字符串（M'SS"）
        """
        if distance_m <= 0 or duration_s <= 0:
            return "0:00"

        # 计算每公里配速（秒）
        pace_sec_per_km = (duration_s / 60) / (distance_m / 1000)
        minutes = int(pace_sec_per_km)
        seconds = int((pace_sec_per_km - minutes) * 60)
        return f"{minutes}:{seconds:02d}"

    def _calculate_total_tss(self, config: ReportConfig) -> float:
        """
        计算总 TSS

        Args:
            config: 报告配置

        Returns:
            float: 总 TSS
        """
        try:
            from datetime import datetime, timedelta

            start_dt = config.start_date
            end_dt = config.end_date

            lf = self.storage.read_parquet()

            # 检查 LazyFrame 是否有列
            if len(lf.collect_schema()) == 0:
                return 0.0

            # 过滤日期范围
            df = lf.filter(pl.col("timestamp").is_between(start_dt, end_dt)).collect()

            if df.is_empty():
                return 0.0

            # 计算每次跑步的 TSS
            total_tss = 0.0
            for row in df.iter_rows(named=True):
                tss = self.analytics.calculate_tss_for_run(
                    distance_m=row.get("total_distance", 0),
                    duration_s=row.get("total_timer_time", 0),
                    avg_heart_rate=row.get("avg_heart_rate"),
                    age=config.age,
                    rest_hr=config.rest_hr,
                )
                total_tss += tss

            return total_tss

        except Exception as e:
            logger.warning(f"计算总 TSS 失败：{e}")
            return 0.0

    def _generate_report_content(
        self,
        report_type: ReportType,
        report_data: Dict[str, Any],
        template_path: Optional[Path] = None,
    ) -> str:
        """
        生成报告内容

        Args:
            report_type: 报告类型
            report_data: 报告数据
            template_path: 自定义模板路径（可选）

        Returns:
            str: 报告内容（Markdown 格式）
        """
        # 创建模板引擎（如果提供了自定义模板）
        template_engine = self.template_engine
        if template_path:
            template_engine = TemplateEngine(template_path=template_path)

        # 获取模板
        template = template_engine.get_template(report_type)

        # 准备模板变量
        variables = self._prepare_template_variables(report_type, report_data)

        # 渲染模板
        content = template_engine.render(template, variables)

        return content

    def _prepare_template_variables(
        self, report_type: ReportType, report_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        准备模板变量

        Args:
            report_type: 报告类型
            report_data: 报告数据

        Returns:
            Dict[str, Any]: 模板变量字典
        """
        variables = {
            # 基础信息
            "start_date": report_data["start_date"],
            "end_date": report_data["end_date"],
            "generated_at": report_data["generated_at"],
            # 训练统计
            "total_runs": report_data["total_runs"],
            "total_distance": report_data["total_distance"],
            "total_duration": report_data["total_duration"],
            "avg_pace": report_data["avg_pace"],
            "avg_hr": report_data["avg_hr"],
            "total_tss": report_data["total_tss"],
            # 训练负荷
            "atl": report_data["atl"],
            "ctl": report_data["ctl"],
            "tsb": report_data["tsb"],
            "fitness_status": report_data["fitness_status"],
            "training_advice": report_data["training_advice"],
        }

        # 格式化心率区间分布
        hr_zones_text = self._format_hr_zones(report_data.get("hr_zones", {}))
        variables["hr_zones"] = hr_zones_text

        # 格式化 VDOT 趋势
        vdot_text = self._format_vdot_trend(report_data.get("vdot_trend", []))
        variables["vdot_trend"] = vdot_text

        # 特定报告类型的额外变量
        if report_type == ReportType.MONTHLY:
            # 月报特有变量
            variables["start_ctl"] = report_data.get("ctl", 0.0)  # 简化处理
            variables["end_ctl"] = report_data["ctl"]
            variables["ctl_change"] = 0.0  # 简化处理
            variables["pace_distribution"] = self._format_pace_distribution(
                report_data.get("pace_distribution", {})
            )

        elif report_type == ReportType.TRAINING_CYCLE:
            # 周期报告特有变量
            cycle_days = (
                datetime.strptime(report_data["end_date"], "%Y-%m-%d")
                - datetime.strptime(report_data["start_date"], "%Y-%m-%d")
            ).days + 1
            cycle_type = self._determine_cycle_type(cycle_days)
            avg_weekly_tss = (
                report_data["total_tss"] / (cycle_days / 7) if cycle_days > 0 else 0.0
            )

            variables["cycle_type"] = cycle_type
            variables["avg_weekly_tss"] = avg_weekly_tss
            variables["start_atl"] = 0.0  # 简化处理
            variables["end_atl"] = report_data["atl"]
            variables["start_ctl"] = 0.0  # 简化处理
            variables["end_ctl"] = report_data["ctl"]
            variables["ctl_change"] = 0.0  # 简化处理
            variables["cycle_evaluation"] = self._generate_cycle_evaluation(report_data)
            variables["next_cycle_advice"] = self._generate_next_cycle_advice(
                report_data, cycle_type
            )
            variables["pace_distribution"] = self._format_pace_distribution(
                report_data.get("pace_distribution", {})
            )

        return variables

    def _format_hr_zones(self, hr_zones_data: Dict[str, Any]) -> str:
        """
        格式化心率区间数据

        Args:
            hr_zones_data: 心率区间数据

        Returns:
            str: 格式化后的文本
        """
        if not hr_zones_data or "zones" not in hr_zones_data:
            return "暂无心率区间数据"

        zones = hr_zones_data.get("zones", [])
        if not zones:
            return "暂无心率区间数据"

        lines = []
        for zone in zones:
            zone_name = zone.get("zone", "")
            zone_label = zone.get("name", "")
            time_seconds = zone.get("time_seconds", 0)
            percentage = zone.get("percentage", 0.0)

            # 转换为分钟
            time_minutes = int(time_seconds / 60)

            lines.append(
                f"- **{zone_name} {zone_label}**: {time_minutes}分钟 ({percentage:.1f}%)"
            )

        return "\n".join(lines) if lines else "暂无有效心率数据"

    def _format_vdot_trend(self, vdot_trend: List[Dict[str, Any]]) -> str:
        """
        格式化 VDOT 趋势数据

        Args:
            vdot_trend: VDOT 趋势数据列表

        Returns:
            str: 格式化后的文本
        """
        if not vdot_trend:
            return "暂无 VDOT 趋势数据"

        lines = []
        for item in vdot_trend[-7:]:  # 只显示最近 7 次
            date = item.get("date", "")
            vdot = item.get("vdot", 0.0)
            distance = item.get("distance", 0.0) / 1000  # 转换为公里

            lines.append(f"- {date}: VDOT {vdot:.1f} ({distance:.1f}km)")

        return "\n".join(lines) if lines else "暂无有效 VDOT 数据"

    def _format_pace_distribution(self, pace_data: Dict[str, Any]) -> str:
        """
        格式化配速分布数据

        Args:
            pace_data: 配速分布数据

        Returns:
            str: 格式化后的文本
        """
        if not pace_data or "zones" not in pace_data:
            return "暂无配速分布数据"

        zones = pace_data.get("zones", {})
        if not zones:
            return "暂无配速分布数据"

        lines = []
        for zone_key, zone_info in zones.items():
            label = zone_info.get("label", zone_key)
            count = zone_info.get("count", 0)
            distance = zone_info.get("distance", 0.0)

            if count > 0:
                lines.append(f"- **{label} ({zone_key})**: {count}次，{distance:.1f}km")

        return "\n".join(lines) if lines else "暂无有效配速数据"

    def _get_report_type_name(self, report_type: ReportType) -> str:
        """
        获取报告类型名称

        Args:
            report_type: 报告类型

        Returns:
            str: 报告类型名称
        """
        names = {
            ReportType.WEEKLY: "周报",
            ReportType.MONTHLY: "月报",
            ReportType.TRAINING_CYCLE: "训练周期报告",
        }
        return names.get(report_type, "报告")

    def _determine_cycle_type(self, cycle_days: int) -> str:
        """
        确定训练周期类型

        Args:
            cycle_days: 周期天数

        Returns:
            str: 周期类型
        """
        if cycle_days <= 7:
            return "小周期"
        elif cycle_days <= 21:
            return "中周期"
        elif cycle_days <= 42:
            return "大周期"
        else:
            return "长周期"

    def _generate_cycle_evaluation(self, report_data: Dict[str, Any]) -> str:
        """
        生成周期评估

        Args:
            report_data: 报告数据

        Returns:
            str: 周期评估文本
        """
        ctl = report_data.get("ctl", 0.0)
        tsb = report_data.get("tsb", 0.0)
        total_tss = report_data.get("total_tss", 0.0)
        total_runs = report_data.get("total_runs", 0)

        evaluations = []

        # 基于 CTL 的评估
        if ctl > 80:
            evaluations.append("体能基础非常扎实，训练水平较高。")
        elif ctl > 50:
            evaluations.append("体能基础良好，训练效果明显。")
        elif ctl > 30:
            evaluations.append("体能基础一般，需继续积累训练量。")
        else:
            evaluations.append("体能基础较弱，建议循序渐进增加训练。")

        # 基于 TSS 的评估
        if total_tss > 500:
            evaluations.append("周期训练负荷较高，训练强度充足。")
        elif total_tss > 300:
            evaluations.append("周期训练负荷适中，训练节奏合理。")
        else:
            evaluations.append("周期训练负荷偏低，可适当增加训练量。")

        # 基于训练次数的评估
        if total_runs >= 5:
            evaluations.append("训练频率良好，保持了规律的训练节奏。")
        elif total_runs >= 3:
            evaluations.append("训练频率一般，建议增加训练次数。")
        else:
            evaluations.append("训练频率较低，需提高训练规律性。")

        return " ".join(evaluations)

    def _generate_next_cycle_advice(
        self, report_data: Dict[str, Any], cycle_type: str
    ) -> str:
        """
        生成下一周期建议

        Args:
            report_data: 报告数据
            cycle_type: 周期类型

        Returns:
            str: 建议文本
        """
        tsb = report_data.get("tsb", 0.0)
        ctl = report_data.get("ctl", 0.0)
        fitness_status = report_data.get("fitness_status", "数据不足")

        advices = []

        # 基于 TSB 状态的建议
        if tsb > 10:
            advices.append("当前状态良好，下一周期可适度增加训练强度。")
        elif tsb > 0:
            advices.append("当前状态正常，建议保持当前训练节奏。")
        elif tsb > -10:
            advices.append("当前有一定疲劳积累，建议适度降低训练强度。")
        else:
            advices.append("警告：疲劳积累过多，建议安排恢复周期。")

        # 基于 CTL 的建议
        if ctl < 30:
            advices.append("建议以有氧基础训练为主，循序渐进增加训练量。")
        elif ctl > 80:
            advices.append("可安排高质量训练课，提升专项能力。")

        # 基于周期类型的建议
        if cycle_type == "小周期":
            advices.append("小周期建议注重训练质量，安排 1-2 次重点训练课。")
        elif cycle_type == "中周期":
            advices.append("中周期建议平衡训练负荷，注重恢复与训练的平衡。")
        elif cycle_type == "大周期":
            advices.append("大周期建议分阶段安排训练，逐步提升训练负荷。")

        return " ".join(advices)

    def save_report(
        self,
        report_content: str,
        report_type: ReportType,
        output_dir: Optional[Path] = None,
        filename: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        保存报告到文件

        Args:
            report_content: 报告内容
            report_type: 报告类型
            output_dir: 输出目录（可选）
            filename: 文件名（可选）

        Returns:
            Dict[str, Any]: 保存结果
        """
        try:
            # 确定输出目录
            if output_dir is None:
                output_dir = self.config.base_dir / "reports"
            output_dir.mkdir(parents=True, exist_ok=True)

            # 确定文件名
            if filename is None:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"{report_type.value}_{timestamp}.md"

            # 保存文件
            file_path = output_dir / filename
            file_path.write_text(report_content, encoding="utf-8")

            logger.info(f"报告已保存：{file_path}")
            return {
                "success": True,
                "file_path": str(file_path),
                "message": f"报告已保存至 {file_path}",
            }

        except Exception as e:
            logger.error(f"保存报告失败：{e}")
            return {"success": False, "error": f"保存失败：{e}"}


# 便捷的报告生成函数
def generate_weekly_report(
    end_date: Optional[datetime] = None,
    age: int = 30,
    template_path: Optional[Path] = None,
) -> Dict[str, Any]:
    """
    生成周报

    Args:
        end_date: 结束日期（不指定则使用今天）
        age: 年龄
        template_path: 自定义模板路径

    Returns:
        Dict[str, Any]: 报告数据
    """
    generator = ReportGenerator()
    return generator.generate_report(
        report_type=ReportType.WEEKLY,
        end_date=end_date,
        age=age,
        template_path=template_path,
    )


def generate_monthly_report(
    end_date: Optional[datetime] = None,
    age: int = 30,
    template_path: Optional[Path] = None,
) -> Dict[str, Any]:
    """
    生成月报

    Args:
        end_date: 结束日期（不指定则使用今天）
        age: 年龄
        template_path: 自定义模板路径

    Returns:
        Dict[str, Any]: 报告数据
    """
    generator = ReportGenerator()
    return generator.generate_report(
        report_type=ReportType.MONTHLY,
        end_date=end_date,
        age=age,
        template_path=template_path,
    )


def generate_training_cycle_report(
    end_date: Optional[datetime] = None,
    age: int = 30,
    template_path: Optional[Path] = None,
) -> Dict[str, Any]:
    """
    生成训练周期报告

    Args:
        end_date: 结束日期（不指定则使用今天）
        age: 年龄
        template_path: 自定义模板路径

    Returns:
        Dict[str, Any]: 报告数据
    """
    generator = ReportGenerator()
    return generator.generate_report(
        report_type=ReportType.TRAINING_CYCLE,
        end_date=end_date,
        age=age,
        template_path=template_path,
    )
