#!/usr/bin/env python3
"""
版本号一致性检查脚本

检查项目中的版本号是否一致，避免发布时版本号不一致的问题。

检查项：
1. pyproject.toml - 项目主版本号
2. README.md - 文档中的版本号
3. CHANGELOG.md - 变更日志中的最新版本号

使用方法：
    python scripts/check_version_consistency.py
"""

import re
import sys
import tomllib
from pathlib import Path


def get_pyproject_version() -> str:
    """从 pyproject.toml 获取版本号"""
    pyproject_path = Path(__file__).parent.parent / "pyproject.toml"
    try:
        with open(pyproject_path, "rb") as f:
            data = tomllib.load(f)
            return data["project"]["version"]
    except Exception as e:
        print(f"❌ 无法读取 pyproject.toml: {e}")
        return ""


def get_readme_version() -> str:
    """从 README.md 获取版本号"""
    readme_path = Path(__file__).parent.parent / "README.md"
    try:
        with open(readme_path, encoding="utf-8") as f:
            content = f.read()
            # 匹配 **最新版本**: v0.9.5 格式
            match = re.search(r"\*\*最新版本\*\*:\s*v(\d+\.\d+\.\d+)", content)
            if match:
                return match.group(1)
            # 匹配 **版本**: v0.9.2 格式
            match = re.search(r"\*\*版本\*\*:\s*v(\d+\.\d+\.\d+)", content)
            if match:
                return match.group(1)
            # 兼容旧的 version-0.9.2 格式
            match = re.search(r"version-(\d+\.\d+\.\d+)", content)
            if match:
                return match.group(1)
    except Exception as e:
        print(f"❌ 无法读取 README.md: {e}")
    return ""


def get_changelog_version() -> str:
    """从 CHANGELOG.md 获取最新版本号"""
    changelog_path = Path(__file__).parent.parent / "CHANGELOG.md"
    try:
        with open(changelog_path, encoding="utf-8") as f:
            content = f.read()
            match = re.search(r"##\s*\[(\d+\.\d+\.\d+)\]", content)
            if match:
                return match.group(1)
    except Exception as e:
        print(f"❌ 无法读取 CHANGELOG.md: {e}")
    return ""


def check_version_consistency() -> bool:
    """检查版本号一致性"""
    print("🔍 检查版本号一致性...")
    print("-" * 60)

    versions = {
        "pyproject.toml": get_pyproject_version(),
        "README.md": get_readme_version(),
        "CHANGELOG.md": get_changelog_version(),
    }

    for source, version in versions.items():
        if version:
            print(f"✅ {source:20s}: v{version}")
        else:
            print(f"❌ {source:20s}: 未找到版本号")

    print("-" * 60)

    version_values = [v for v in versions.values() if v]
    if not version_values:
        print("❌ 未找到任何版本号")
        return False

    if len(set(version_values)) == 1:
        print(f"✅ 版本号一致: v{version_values[0]}")
        return True
    else:
        print("❌ 版本号不一致:")
        for source, version in versions.items():
            if version:
                print(f"   - {source}: v{version}")
        return False


def main():
    """主函数"""
    success = check_version_consistency()
    if success:
        print("\n✅ 版本号检查通过")
        sys.exit(0)
    else:
        print("\n❌ 版本号检查失败")
        sys.exit(1)


if __name__ == "__main__":
    main()
