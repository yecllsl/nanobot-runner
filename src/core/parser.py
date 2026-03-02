# FIT文件解析器
# 基于fitparse库解析.fit格式文件

import fitparse
import polars as pl
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any


class FitParser:
    """FIT文件解析器"""
    
    def __init__(self):
        """初始化解析器"""
        pass
    
    def parse_file(self, filepath: Path) -> Optional[pl.DataFrame]:
        """
        解析单个FIT文件
        
        Args:
            filepath: FIT文件路径
            
        Returns:
            pl.DataFrame: 解析后的数据框，失败返回None
        """
        try:
            fit_file = fitparse.FitFile(str(filepath))
            
            records = []
            session_data = None
            
            for record in fit_file.get_messages("record"):
                record_data = {}
                for data in record:
                    record_data[data.name] = data.value
                records.append(record_data)
            
            for session in fit_file.get_messages("session"):
                session_data = {}
                for data in session:
                    session_data[data.name] = data.value
            
            if not records:
                print(f"警告: 文件 {filepath} 没有记录数据")
                return None
            
            # 转换为Polars DataFrame
            df = pl.DataFrame(records)
            
            # 添加会话信息（如果存在）
            if session_data:
                for key, value in session_data.items():
                    if key not in df.columns:
                        df = df.with_columns(pl.lit(value).alias(key))
            
            # 添加文件元数据
            df = df.with_columns([
                pl.lit(str(filepath)).alias("source_file"),
                pl.lit(filepath.stem).alias("filename")
            ])
            
            return df
            
        except Exception as e:
            print(f"解析错误 (文件: {filepath}): {e}")
            return None
    
    def parse_file_metadata(self, filepath: Path) -> Dict[str, Any]:
        """
        解析FIT文件元数据（用于生成指纹）
        
        Args:
            filepath: FIT文件路径
            
        Returns:
            dict: 元数据字典
        """
        try:
            fit_file = fitparse.FitFile(str(filepath))
            
            metadata = {
                "serial_number": None,
                "time_created": None,
                "total_distance": None,
                "filename": filepath.stem,
                "filepath": str(filepath)
            }
            
            for record in fit_file.get_messages("file_id"):
                for data in record:
                    if data.name == "serial_number":
                        metadata["serial_number"] = data.value
                    elif data.name == "time_created":
                        metadata["time_created"] = data.value
                    elif data.name == "total_distance":
                        metadata["total_distance"] = data.value
            
            return metadata
            
        except Exception as e:
            print(f"解析元数据失败 (文件: {filepath}): {e}")
            return {
                "serial_number": None,
                "time_created": None,
                "total_distance": None,
                "filename": filepath.stem,
                "filepath": str(filepath)
            }
