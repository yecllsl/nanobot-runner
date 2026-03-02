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
        
        if not files:
            return pl.LazyFrame()
        
        # 使用 LazyFrame 进行延迟加载
        lazy_frames = [pl.scan_parquet(f) for f in files]
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
