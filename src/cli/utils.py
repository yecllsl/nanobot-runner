# CLI 工具函数
# 提供模板同步等辅助功能

from pathlib import Path


def sync_custom_templates(workspace: Path) -> list[str]:
    """
    同步自定义模板文件到 workspace 目录

    将项目 templates/ 目录下的自定义模板文件复制到用户的 workspace 目录，
    覆盖 nanobot-ai 框架生成的默认模板。

    Args:
        workspace: workspace 目录路径（如 ~/.nanobot-runner/）

    Returns:
        list[str]: 已同步的模板文件名列表
    """
    synced: list[str] = []

    # 项目模板目录
    # __file__ = src/cli/utils.py -> parent.parent.parent = 项目根目录
    project_templates_dir = Path(__file__).parent.parent.parent / "templates"

    if not project_templates_dir.exists():
        return synced

    # 需要同步的模板文件列表
    template_files = ["SOUL.md", "AGENTS.md", "USER.md"]

    for template_name in template_files:
        src_file = project_templates_dir / template_name

        if not src_file.exists():
            continue

        # 目标文件路径
        dst_file = workspace / template_name

        # 复制文件（覆盖）
        try:
            import shutil

            shutil.copy2(src_file, dst_file)
            synced.append(template_name)
        except Exception:
            continue

    return synced
