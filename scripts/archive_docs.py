#!/usr/bin/env python3
"""
文档归档脚本 - 将版本相关文档移动到归档目录
"""
import shutil
import os
from pathlib import Path


def move_files_by_pattern(source_dir: str, dest_dir: str, pattern: str):
    """移动匹配模式的文件到目标目录"""
    source = Path(source_dir)
    dest = Path(dest_dir)
    dest.mkdir(parents=True, exist_ok=True)
    
    moved = []
    for file_path in source.rglob(pattern):
        if file_path.is_file():
            try:
                target = dest / file_path.name
                shutil.move(str(file_path), str(target))
                moved.append(file_path.name)
                print(f"✅ 已移动: {file_path.name}")
            except Exception as e:
                print(f"❌ 移动失败 {file_path.name}: {e}")
    
    return moved


def main():
    base_dir = Path("docs")
    archive_dir = base_dir / "archive"
    
    # v0.13.0 归档
    print("\n📦 归档 v0.13.0 文档...")
    v013_dirs = {
        "development": base_dir / "development",
        "devops": base_dir / "devops",
        "test": base_dir / "test",
        "test_reports": base_dir / "test" / "reports",
    }
    
    for category, source in v013_dirs.items():
        if source.exists():
            dest = archive_dir / "v0.13.0" / (category.replace("_reports", ""))
            files = move_files_by_pattern(str(source), str(dest), "*v0.13.0*")
            if files:
                print(f"  📁 {category}: {len(files)} 个文件")
    
    # v0.12.0 归档
    print("\n📦 归档 v0.12.0 文档...")
    v012_dirs = {
        "development": base_dir / "development",
        "devops": base_dir / "devops",
        "test": base_dir / "test",
        "test_reports": base_dir / "test" / "reports",
    }
    
    for category, source in v012_dirs.items():
        if source.exists():
            dest = archive_dir / "v0.12.0" / (category.replace("_reports", ""))
            files = move_files_by_pattern(str(source), str(dest), "*v0.12.0*")
            if files:
                print(f"  📁 {category}: {len(files)} 个文件")
    
    print("\n✅ 文档归档完成!")


if __name__ == "__main__":
    main()
