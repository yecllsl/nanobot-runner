#!/usr/bin/env python3
"""修复README.md版本号"""
import re
from pathlib import Path

readme_path = Path(__file__).parent.parent / "README.md"
content = readme_path.read_text(encoding="utf-8")

# 替换所有v0.9.4为v0.12.0（在版本相关上下文中）
content = re.sub(r'\*\*版本\*\*:\s*v0\.9\.4', '**版本**: v0.12.0', content)
content = re.sub(r'\(v0\.9\.4\)', '(v0.12.0)', content)

readme_path.write_text(content, encoding="utf-8")
print("✅ README.md版本号已更新为v0.12.0")
