#!/usr/bin/env python3
"""
更新归档zip文件脚本
"""
import shutil
import zipfile
from pathlib import Path


def update_archive_zip(version: str):
    """更新指定版本的归档zip文件"""
    archive_dir = Path(f"docs/archive/{version}")
    zip_path = Path(f"docs/archive/{version}-archive.zip")
    
    # 检查归档目录是否存在
    if not archive_dir.exists():
        print(f"⚠️ 归档目录不存在: {archive_dir}")
        return False
    
    # 删除旧的zip文件
    if zip_path.exists():
        zip_path.unlink()
        print(f"🗑️ 已删除旧zip: {zip_path.name}")
    
    # 创建新的zip文件
    try:
        shutil.make_archive(
            str(zip_path.with_suffix('')),
            'zip',
            str(archive_dir.parent),
            str(archive_dir.name)
        )
        print(f"✅ 已创建新zip: {zip_path.name}")
        
        # 显示文件大小
        size = zip_path.stat().st_size
        print(f"   文件大小: {size / 1024:.1f} KB")
        return True
    except Exception as e:
        print(f"❌ 创建zip失败: {e}")
        return False


def main():
    versions = ["v0.13.0", "v0.12.0"]
    
    for version in versions:
        print(f"\n📦 更新 {version} 归档...")
        update_archive_zip(version)
    
    print("\n✅ 归档zip更新完成!")


if __name__ == "__main__":
    main()
