# Parquet存储管理器
# 管理跑步数据的Parquet文件读写

import polars as pl
from pathlib import Path
from typing import Optional, List


class StorageManager:
    """Parquet存储管理器，管理跑步数据的存储"""
    
    def __init__(self, data_dir: Optional[Path] = None):
        """
        初始化存储管理器
        
        Args:
            data_dir: 数据目录路径，不指定则使用默认目录
        """
        self.data_dir = data_dir or Path.home() / ".nanobot-runner" / "data"
        self.data_dir.mkdir(parents=True, exist_ok=True)
    
    def save_to_parquet(self, dataframe: pl.DataFrame, year: int) -> bool:
        """
        保存数据到Parquet文件（按年份分片）
        
        Args:
            dataframe: Polars DataFrame数据
            year: 年份
            
        Returns:
            bool: 保存是否成功
        """
        try:
            # 检查数据框是否为空
            if dataframe.height == 0:
                print(f"警告: 数据为空，跳过保存")
                return False
            
            filename = f"activities_{year}.parquet"
            filepath = self.data_dir / filename
            
            # 如果文件已存在，追加写入
            if filepath.exists():
                existing_df = pl.read_parquet(filepath)
                combined_df = pl.concat([existing_df, dataframe])
                combined_df.write_parquet(filepath, compression='snappy')
            else:
                dataframe.write_parquet(filepath, compression='snappy')
            
            return True
        except Exception as e:
            print(f"保存失败: {e}")
            return False
    
    def save_activities(self, dataframe: pl.DataFrame) -> dict:
        """
        保存跑步活动数据（兼容接口）
        
        Args:
            dataframe: Polars DataFrame数据，必须包含'timestamp'和'year'列
            
        Returns:
            dict: 保存结果字典，包含'success'、'message'、'records_saved'和'year'键
        """
        try:
            # 检查数据框是否为空
            if dataframe.height == 0:
                return {"success": False, "message": "数据为空", "records_saved": 0, "year": None}
            
            # 从数据中提取年份
            year = dataframe.select(pl.col("year")).row(0)[0]
            success = self.save_to_parquet(dataframe, year)
            if success:
                return {"success": True, "message": "保存成功", "records_saved": dataframe.height, "year": year}
            else:
                return {"success": False, "message": "保存失败", "records_saved": 0, "year": year}
        except Exception as e:
            return {"success": False, "message": f"保存失败: {e}", "records_saved": 0, "year": None}
    
    def load_activities(self, years: Optional[List[int]] = None) -> pl.DataFrame:
        """
        加载跑步活动数据
        
        Args:
            years: 要加载的年份列表，None表示加载所有年份
            
        Returns:
            pl.DataFrame: 加载的数据框
        """
        lazy_frame = self.read_parquet(years)
        return lazy_frame.collect()
    
    def read_parquet(self, years: Optional[List[int]] = None) -> pl.LazyFrame:
        """
        读取Parquet文件
        
        Args:
            years: 要读取的年份列表，None表示读取所有年份
            
        Returns:
            pl.LazyFrame: Polars LazyFrame
        """
        if years is None:
            # 读取所有年份文件
            files = list(self.data_dir.glob("activities_*.parquet"))
        else:
            files = [self.data_dir / f"activities_{year}.parquet" for year in years]
        
        # 过滤掉不存在的文件
        existing_files = [f for f in files if f.exists()]
        
        if not existing_files:
            return pl.LazyFrame()
        
        # 使用 LazyFrame 进行延迟加载
        lazy_frames = [pl.scan_parquet(f) for f in existing_files]
        return pl.concat(lazy_frames)
    
    def get_stats(self) -> dict:
        """
        获取数据统计信息
        
        Returns:
            dict: 统计信息
        """
        try:
            lf = self.read_parquet()
            
            if lf.collect().height == 0:
                return {
                    "total_records": 0,
                    "time_range": None,
                    "years": []
                }
            
            df = lf.collect()
            
            # 获取年份列表
            years = sorted(set(
                df.select(pl.col("timestamp").dt.year()).to_series().to_list()
            ))
            
            # 获取时间范围
            min_time = df.select(pl.col("timestamp").min()).item()
            max_time = df.select(pl.col("timestamp").max()).item()
            
            return {
                "total_records": df.height,
                "time_range": {
                    "start": str(min_time),
                    "end": str(max_time)
                },
                "years": years
            }
        except Exception as e:
            return {
                "total_records": 0,
                "time_range": None,
                "years": [],
                "error": str(e)
            }
    
    def query_activities(self, years: Optional[List[int]] = None, 
                        days: Optional[int] = None,
                        min_distance: Optional[float] = None,
                        min_heart_rate: Optional[int] = None) -> pl.DataFrame:
        """
        查询跑步活动数据（兼容接口）
        
        Args:
            years: 要查询的年份列表，None表示查询所有年份
            days: 查询最近N天的数据，优先级高于years
            min_distance: 最小距离过滤
            min_heart_rate: 最小心率过滤
            
        Returns:
            pl.DataFrame: 查询结果
        """
        lf = self.read_parquet(years)
        
        if days is not None:
            from datetime import datetime, timedelta
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)
            start_str = start_date.strftime("%Y-%m-%d")
            end_str = end_date.strftime("%Y-%m-%d")
            
            lf = lf.filter(pl.col("timestamp") >= start_str).filter(pl.col("timestamp") <= end_str)
        
        if min_distance is not None:
            lf = lf.filter(pl.col("total_distance") >= min_distance)
        
        if min_heart_rate is not None:
            lf = lf.filter(pl.col("avg_heart_rate") >= min_heart_rate)
        
        return lf.collect()
