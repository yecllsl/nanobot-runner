# 数据导入服务
# 编排解析、索引、存储等模块，实现数据导入功能

import polars as pl
from pathlib import Path
from typing import List, Dict, Any, Optional
from rich.console import Console
from rich.progress import Progress, TaskID

from src.core.parser import FitParser
from src.core.indexer import IndexManager
from src.core.storage import StorageManager


class ImportService:
    """数据导入服务"""
    
    def __init__(self):
        """初始化导入服务"""
        self.console = Console()
        self.parser = FitParser()
        self.indexer = IndexManager()
        self.storage = StorageManager()
    
    def scan_directory(self, directory: Path) -> List[Path]:
        """
        扫描目录下的所有FIT文件
        
        Args:
            directory: 目录路径
            
        Returns:
            list: FIT文件路径列表
        """
        return list(directory.rglob("*.fit"))
    
    def process_file(self, filepath: Path, progress: Progress, task_id: TaskID) -> Dict[str, Any]:
        """
        处理单个FIT文件
        
        Args:
            filepath: FIT文件路径
            progress: 进度条对象
            task_id: 任务ID
            
        Returns:
            dict: 处理结果
        """
        result = {
            "filepath": str(filepath),
            "filename": filepath.stem,
            "status": "skipped",
            "message": ""
        }
        
        # 解析元数据生成指纹
        metadata = self.parser.parse_file_metadata(filepath)
        if not metadata.get("serial_number"):
            result["message"] = "无法解析文件元数据"
            progress.update(task_id, advance=1)
            return result
        
        fingerprint = self.indexer.generate_fingerprint(metadata)
        
        # 检查是否已存在
        if self.indexer.exists(fingerprint):
            result["message"] = "文件已存在（重复）"
            progress.update(task_id, advance=1)
            return result
        
        # 解析数据
        df = self.parser.parse_file(filepath)
        if df is None:
            result["message"] = "解析失败"
            progress.update(task_id, advance=1)
            return result
        
        # 获取年份
        try:
            year = df.select(pl.col("timestamp").dt.year()).row(0)[0]
        except Exception:
            year = 2024
        
        # 保存到Parquet
        if self.storage.save_to_parquet(df, year):
            # 添加到索引
            self.indexer.add(fingerprint, metadata)
            result["status"] = "added"
            result["message"] = "导入成功"
            result["fingerprint"] = fingerprint
        else:
            result["message"] = "保存失败"
        
        progress.update(task_id, advance=1)
        return result
    
    def import_file(self, filepath: Path) -> Dict[str, Any]:
        """
        导入单个文件
        
        Args:
            filepath: FIT文件路径
            
        Returns:
            dict: 导入结果
        """
        self.console.print(f"[bold]正在处理: {filepath.name}[/bold]")
        
        metadata = self.parser.parse_file_metadata(filepath)
        if not metadata.get("serial_number"):
            self.console.print("[red]错误: 无法解析文件元数据[/red]")
            return {"status": "error", "message": "无法解析元数据"}
        
        fingerprint = self.indexer.generate_fingerprint(metadata)
        
        if self.indexer.exists(fingerprint):
            self.console.print(f"[yellow]跳过: 文件已存在 ({filepath.name})[/yellow]")
            return {"status": "skipped", "message": "文件已存在"}
        
        df = self.parser.parse_file(filepath)
        if df is None:
            self.console.print("[red]错误: 解析失败[/red]")
            return {"status": "error", "message": "解析失败"}
        
        try:
            year = df.select(pl.col("timestamp").dt.year()).row(0)[0]
        except Exception:
            year = 2024
        
        if self.storage.save_to_parquet(df, year):
            self.indexer.add(fingerprint, metadata)
            self.console.print(f"[green]新增: 导入成功 ({filepath.name})[/green]")
            return {"status": "added", "message": "导入成功", "fingerprint": fingerprint}
        else:
            self.console.print("[red]错误: 保存失败[/red]")
            return {"status": "error", "message": "保存失败"}
    
    def import_directory(self, directory: Path) -> Dict[str, Any]:
        """
        批量导入目录
        
        Args:
            directory: 目录路径
            
        Returns:
            dict: 导入统计
        """
        fit_files = self.scan_directory(directory)
        
        if not fit_files:
            self.console.print("[yellow]警告: 未找到FIT文件[/yellow]")
            return {"total": 0, "added": 0, "skipped": 0, "errors": 0}
        
        self.console.print(f"[bold]发现 {len(fit_files)} 个FIT文件[/bold]")
        
        added = 0
        skipped = 0
        errors = 0
        
        with Progress() as progress:
            task = progress.add_task("正在导入...", total=len(fit_files))
            
            for filepath in fit_files:
                result = self.import_file(filepath)
                
                if result["status"] == "added":
                    added += 1
                elif result["status"] == "skipped":
                    skipped += 1
                else:
                    errors += 1
        
        self.console.print("\n" + "=" * 50)
        self.console.print(f"[bold]导入完成:[/bold]")
        self.console.print(f"  新增: [green]{added}[/green] 条记录")
        self.console.print(f"  跳过: [yellow]{skipped}[/yellow] 条重复")
        self.console.print(f"  错误: [red]{errors}[/red] 个")
        
        return {"total": len(fit_files), "added": added, "skipped": skipped, "errors": errors}
