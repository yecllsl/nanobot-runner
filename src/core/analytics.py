# 分析引擎
# 基于Polars实现核心数据分析算法

import polars as pl
from typing import Optional, Dict, Any, List


class AnalyticsEngine:
    """数据分析引擎"""
    
    def __init__(self, storage_manager):
        """
        初始化分析引擎
        
        Args:
            storage_manager: StorageManager实例
        """
        self.storage = storage_manager
    
    def calculate_vdot(self, distance_m: float, time_s: float) -> float:
        """
        计算VDOT值（跑力值）
        
        Args:
            distance_m: 距离（米）
            time_s: 用时（秒）
            
        Returns:
            float: VDOT值
        """
        # 使用Powers公式计算VDOT
        # VDOT = (0.0001 * distance^1.06 * 24.6) / time^0.43
        if distance_m <= 0 or time_s <= 0:
            return 0.0
        
        vdot = (0.0001 * (distance_m ** 1.06) * 24.6) / (time_s ** 0.43)
        return round(vdot, 2)
    
    def calculate_tss(self, heart_rate_data: pl.Series, duration_s: float, 
                      ftp: int = 200) -> float:
        """
        计算训练压力分数（TSS）
        
        Args:
            heart_rate_data: 心率数据序列
            duration_s: 时长（秒）
            ftp: 功能阈值功率（默认200）
            
        Returns:
            float: TSS值
        """
        if len(heart_rate_data) == 0 or duration_s <= 0:
            return 0.0
        
        # 计算平均心率
        avg_hr = heart_rate_data.mean()
        
        # 假设最大心率为220 - 年龄（默认30岁）
        max_hr = 190
        rest_hr = 60
        
        # 计算强度因子（IF）
        if avg_hr <= rest_hr:
            return 0.0
        
        ift = (avg_hr - rest_hr) / (max_hr - rest_hr)
        
        # TSS = (duration * IF * IFT) / (3600 * 100) * 100
        tss = (duration_s * 1.0 * ift) / 3600 * 100
        
        return round(tss, 2)
    
    def get_running_summary(self, start_date: Optional[str] = None, 
                           end_date: Optional[str] = None) -> pl.DataFrame:
        """
        获取跑步摘要统计
        
        Args:
            start_date: 开始日期
            end_date: 结束日期
            
        Returns:
            pl.DataFrame: 摘要数据
        """
        lf = self.storage.read_parquet()
        
        if start_date:
            lf = lf.filter(pl.col("timestamp") >= start_date)
        if end_date:
            lf = lf.filter(pl.col("timestamp") <= end_date)
        
        df = lf.collect()
        
        if df.height == 0:
            return df
        
        # 计算摘要统计
        summary = df.select([
            pl.count().alias("total_runs"),
            pl.col("distance").sum().alias("total_distance"),
            pl.col("duration").sum().alias("total_duration"),
            pl.col("distance").mean().alias("avg_distance"),
            pl.col("duration").mean().alias("avg_duration"),
            pl.col("distance").max().alias("max_distance"),
            pl.col("heart_rate").mean().alias("avg_heart_rate")
        ])
        
        return summary
    
    def analyze_hr_drift(self, heart_rate: List[float], pace: List[float]) -> Dict[str, Any]:
        """
        分析心率漂移
        
        Args:
            heart_rate: 心率列表
            pace: 配速列表
            
        Returns:
            dict: 心率漂移分析结果
        """
        if len(heart_rate) < 10 or len(pace) < 10:
            return {"error": "数据量不足"}
        
        hr_series = pl.Series(heart_rate)
        pace_series = pl.Series(pace)
        
        # 计算相关性
        # Polars 1.x 使用 corr_to 方法
        try:
            correlation = hr_series.corr(pace_series)
        except AttributeError:
            # 如果 corr 方法不存在，使用 DataFrame 计算
            df = pl.DataFrame({"hr": hr_series, "pace": pace_series})
            correlation = df.select(pl.corr("hr", "pace")).item()
        
        # 检测心率漂移拐点（后半段心率上升）
        mid_point = len(heart_rate) // 2
        first_half_avg = sum(heart_rate[:mid_point]) / mid_point
        second_half_avg = sum(heart_rate[mid_point:]) / (len(heart_rate) - mid_point)
        
        hr_drift = second_half_avg - first_half_avg
        
        return {
            "correlation": round(correlation, 4),
            "first_half_avg_hr": round(first_half_avg, 2),
            "second_half_avg_hr": round(second_half_avg, 2),
            "hr_drift": round(hr_drift, 2),
            "has_drift": hr_drift > 5
        }
    
    def calculate_atl_ctl(self, tss_data: List[float], window_size: int = 42) -> Dict[str, List[float]]:
        """
        计算急性负荷（ATL）和慢性负荷（CTL）
        
        Args:
            tss_data: TSS数据列表
            window_size: 窗口大小（默认42天）
            
        Returns:
            dict: ATL和CTL序列
        """
        if not tss_data:
            return {"atl": [], "ctl": []}
        
        atl = []
        ctl = []
        
        # ATL = 7天指数移动平均
        # CTL = 42天指数移动平均
        atl_alpha = 1 / 7
        ctl_alpha = 1 / 42
        
        atl_value = tss_data[0]
        ctl_value = tss_data[0]
        
        for tss in tss_data:
            atl_value = atl_alpha * tss + (1 - atl_alpha) * atl_value
            ctl_value = ctl_alpha * tss + (1 - ctl_alpha) * ctl_value
            
            atl.append(round(atl_value, 2))
            ctl.append(round(ctl_value, 2))
        
        return {"atl": atl, "ctl": ctl}
