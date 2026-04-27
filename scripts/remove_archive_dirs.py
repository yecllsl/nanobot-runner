#!/usr/bin/env python3
"""
删除归档目录脚本 - 删除已压缩的原始归档目录
"""
import shutil
from pathlib import Path


def remove_archive_dir(version: str):
    """删除指定版本的归档目录"""
    archive_dir = Path(f"docs/archive/{version}")
    zip_file = Path(f"docs/archive/{version}-archive.zip")
    
    # 检查zip文件是否存在
    if not zip_file.exists():
        print(f"❌ {zip_file.name} 不存在，跳过删除")
        return False
    
    # 检查zip文件大小
    if zip_file.stat().st_size == 0:
        print(f"❌ {zip_file.name} 大小为0，跳过删除")
        return False
    
    # 删除目录
    if archive_dir.exists():
        try:
            shutil.rmtree(archive_dir)
            print(f"✅ 已删除: {archive_dir}")
            return True
        except Exception as e:
            print(f"❌ 删除失败 {archive_dir}: {e}")
            return False
    else:
        print(f"⚠️ {archive_dir} 不存在")
        return True


def main():
    versions = ["v0.13.0", "v0.12.0"]
    
    for version in versions:
        print(f"\n📁 处理 {version}...")
        remove_archive_dir(version)
    
    print("\n✅ 归档目录清理完成!")


if __name__ == "__main__":
    main()
