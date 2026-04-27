#!/usr/bin/env python3
"""
归档遗漏文档脚本
"""
import shutil
from pathlib import Path


def archive_missing_docs():
    """归档遗漏的文档"""
    
    # 需要归档的文档列表
    missing_docs = [
        # v0.13.0 相关
        ("docs/development/开发交付报告_T01315_天气训练协同.md", "docs/archive/v0.13.0/development/"),
        
        # v0.12.0 相关
        ("docs/test/reports/测试报告_v0.12.md", "docs/archive/v0.12.0/test/"),
        ("docs/test/strategy_v0.12.md", "docs/archive/v0.12.0/test/"),
    ]
    
    for source_path, dest_dir in missing_docs:
        source = Path(source_path)
        dest = Path(dest_dir)
        
        if source.exists():
            dest.mkdir(parents=True, exist_ok=True)
            try:
                shutil.move(str(source), str(dest / source.name))
                print(f"✅ 已归档: {source.name}")
            except Exception as e:
                print(f"❌ 归档失败 {source.name}: {e}")
        else:
            print(f"⚠️ 文件不存在: {source_path}")


if __name__ == "__main__":
    archive_missing_docs()
    print("\n✅ 遗漏文档归档完成!")
