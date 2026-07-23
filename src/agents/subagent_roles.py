"""Subagent 角色定义模块

定义专业 subagent 的角色 prompt 和注册表。每个角色是纯数据（SubagentRole），
由 RunnerTools 在 _prepare_subagent_context 中按角色预查询数据，
再通过 build_task 拼装为 nanobot-ai SpawnTool 可识别的 task 字符串。

设计原则（ponytail）：
- 纯数据，无抽象，无反射调用
- 新增角色 = 在 ROLES 加一条
- prompt 片段由 build_task 注入 task 开头，subagent 按.task 行事
"""

from __future__ import annotations

import json
from dataclasses import dataclass

# 教练角色系统 prompt 片段
COACH_PROMPT: str = """你是资深跑步教练，专精于基于 VDOT 和训练负荷数据的训练计划制定。
你的职责：
- 分析近期训练数据，给出配速和训练量建议
- 基于数字孪生推演结果，推荐训练方案
- 调整训练计划以逼近用户目标赛事
你不负责伤病诊断、营养建议、装备选择。
输出格式：结构化建议 + 理由 + 可执行动作。"""


# 伤病预防师角色系统 prompt 片段
INJURY_PROMPT: str = """你是运动医学背景的伤病预防师，基于伤病风险预测模型和身体信号数据工作。
你的职责：
- 解读伤病风险预测结果（ML/参数化/规则三层降级）
- 识别急性负荷过高、HRV 异常、心率漂移过大等风险信号
- 给出恢复建议（休息/减量/交叉训练）
- 标记需要停止训练的红线信号
你不负责训练计划制定、营养建议。
输出格式：风险等级 + 风险因素 + 恢复建议 + 红线警告（如有）。"""


@dataclass(frozen=True)
class SubagentRole:
    """Subagent 角色定义（纯数据）

    Attributes:
        name: 角色名（与 ROLES key 一致，用于 spawn_subagent 的 subagent_type 参数）
        prompt: 角色系统 prompt 片段，注入 task 开头定义 subagent 行为
        context_builders: 预查询方法名元组（文档性，MVP 不做反射调用）
    """

    name: str
    prompt: str
    context_builders: tuple[str, ...]

    def build_task(self, user_request: str, context_data: dict) -> str:
        """拼装 task：角色 prompt + 用户请求 + 数据上下文

        Args:
            user_request: 用户原始请求
            context_data: 预查询数据字典（含 memory 字段）

        Returns:
            str: 组装后的 task 字符串，格式：
                {prompt}\n\n用户请求：{request}\n---数据上下文---\n{json}\n---数据上下文结束---
        """
        # 延迟导入避免循环：从 tools（入口模块）取 SpawnSubagentTool 的常量。
        # 不能直接 import tools_twin：subagent_roles 被单独导入时，tools_twin → tools
        # → (line 2788) tools_twin 部分初始化 → ImportError。tools.py 是设计好的入口，
        # 它在 BaseTool 定义后才 import tools_twin，故经 tools 取类是循环安全的。
        from src.agents.tools import SpawnSubagentTool

        return (
            f"{self.prompt}\n\n"
            f"用户请求：{user_request}\n"
            f"{SpawnSubagentTool.CONTEXT_SEPARATOR}"
            f"{json.dumps(context_data, ensure_ascii=False, default=str, indent=2)}"
            f"{SpawnSubagentTool.CONTEXT_END}"
        )


# 角色注册表：新增角色在此添加一条即可
ROLES: dict[str, SubagentRole] = {
    "coach": SubagentRole(
        name="coach",
        prompt=COACH_PROMPT,
        context_builders=(
            "get_vdot_trend",
            "get_training_load",
            "get_recent_runs",
            "_get_plan_status_safe",
            "_load_subagent_memory",
        ),
    ),
    "injury_prevention": SubagentRole(
        name="injury_prevention",
        prompt=INJURY_PROMPT,
        context_builders=(
            "predict_injury_risk",
            "get_hrv_analysis",
            "get_fatigue_score",
            "get_recovery_status",
            "get_hr_drift_analysis",
            "get_training_load",
            "_load_subagent_memory",
        ),
    ),
}
