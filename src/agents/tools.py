# Agent工具集
# 封装为nanobot-ai可识别的工具

import polars as pl
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta

from src.core.storage import StorageManager
from src.core.analytics import AnalyticsEngine


class RunnerTools:
    """跑步助理工具集"""
    
    def __init__(self, storage: Optional[StorageManager] = None):
        """
        初始化工具集
        
        Args:
            storage: StorageManager实例
        """
        self.storage = storage or StorageManager()
        self.analytics = AnalyticsEngine(self.storage)
    
    def get_running_stats(self, start_date: Optional[str] = None, 
                         end_date: Optional[str] = None) -> Dict[str, Any]:
        """
        获取跑步统计数据
        
        Args:
            start_date: 开始日期（可选）
            end_date: 结束日期（可选）
            
        Returns:
            dict: 统计数据
        """
        summary = self.analytics.get_running_summary(start_date, end_date)
        
        if summary.height == 0:
            return {"message": "暂无跑步数据"}
        
        row = summary.row(0)
        
        return {
            "total_runs": row[0],
            "total_distance": row[1],
            "total_duration": row[2],
            "avg_distance": row[3],
            "avg_duration": row[4],
            "max_distance": row[5],
            "avg_heart_rate": row[6]
        }
    
    def get_recent_runs(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        获取最近跑步记录
        
        Args:
            limit: 返回数量限制
            
        Returns:
            list: 跑步记录列表
        """
        lf = self.storage.read_parquet()
        df = lf.sort(pl.col("timestamp").sort(descending=True)).limit(limit).collect()
        
        runs = []
        for row in df.iter_rows(named=True):
            runs.append({
                "timestamp": str(row.get("timestamp", "N/A")),
                "distance": row.get("distance", 0),
                "duration": row.get("duration", 0),
                "heart_rate": row.get("heart_rate", "N/A")
            })
        
        return runs
    
    def calculate_vdot_for_run(self, distance_m: float, time_s: float) -> float:
        """
        计算单次跑步的VDOT值
        
        Args:
            distance_m: 距离（米）
            time_s: 用时（秒）
            
        Returns:
            float: VDOT值
        """
        return self.analytics.calculate_vdot(distance_m, time_s)
    
    def get_vdot_trend(self, limit: int = 20) -> List[Dict[str, Any]]:
        """
        获取VDOT趋势
        
        Args:
            limit: 返回数量限制
            
        Returns:
            list: VDOT趋势数据
        """
        lf = self.storage.read_parquet()
        df = lf.sort(pl.col("timestamp").sort(descending=True)).limit(limit).collect()
        
        vdot_trend = []
        for row in df.iter_rows(named=True):
            distance = row.get("distance", 0)
            duration = row.get("duration", 0)
            
            if distance > 0 and duration > 0:
                vdot = self.analytics.calculate_vdot(distance, duration)
                vdot_trend.append({
                    "timestamp": str(row.get("timestamp", "N/A")),
                    "distance": distance,
                    "vdot": vdot
                })
        
        return vdot_trend
    
    def get_hr_drift_analysis(self, run_id: Optional[str] = None) -> Dict[str, Any]:
        """
        获取心率漂移分析
        
        Args:
            run_id: 活动ID（可选）
            
        Returns:
            dict: 心率漂移分析结果
        """
        lf = self.storage.read_parquet()
        df = lf.collect()
        
        if df.height == 0:
            return {"error": "暂无数据"}
        
        # 获取心率和配速数据
        heart_rate = df.select(pl.col("heart_rate")).to_series().to_list()
        pace = df.select(pl.col("pace")).to_series().to_list()
        
        return self.analytics.analyze_hr_drift(heart_rate, pace)
    
    def get_training_load(self, days: int = 42) -> Dict[str, Any]:
        """
        获取训练负荷（ATL/CTL）
        
        Args:
            days: 分析天数
            
        Returns:
            dict: 训练负荷数据
        """
        # TODO: 实现基于TSS的训练负荷计算
        return {
            "message": "训练负荷计算功能待实现",
            "note": "需要先计算每条记录的TSS值"
        }


# 工具描述（供Agent使用）
TOOL_DESCRIPTIONS = {
    "get_running_stats": {
        "description": "获取跑步统计数据，包括总次数、总距离、平均距离等",
        "parameters": {
            "start_date": "开始日期（可选，格式：YYYY-MM-DD）",
            "end_date": "结束日期（可选，格式：YYYY-MM-DD）"
        }
    },
    "get_recent_runs": {
        "description": "获取最近的跑步记录",
        "parameters": {
            "limit": "返回数量限制（默认10条）"
        }
    },
    "calculate_vdot_for_run": {
        "description": "计算单次跑步的VDOT值（跑力值）",
        "parameters": {
            "distance_m": "距离（米）",
            "time_s": "用时（秒）"
        }
    },
    "get_vdot_trend": {
        "description": "获取VDOT趋势变化",
        "parameters": {
            "limit": "返回数量限制（默认20条）"
        }
    },
    "get_hr_drift_analysis": {
        "description": "分析心率漂移情况",
        "parameters": {
            "run_id": "活动ID（可选）"
        }
    },
    "get_training_load": {
        "description": "获取训练负荷（ATL/CTL）",
        "parameters": {
            "days": "分析天数（默认42天）"
        }
    }
}
