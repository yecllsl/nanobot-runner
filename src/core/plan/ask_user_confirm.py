"""
ask_user 异步确认模块 - v0.17.0 (实验性功能)

实现异步用户确认模式。Agent 通过输出结构化选项+确认提示，
用户在下一轮对话中确认。不支持同步阻塞模式（底座不支持）。

使用场景：
1. 训练计划确认 - 输出结构化选项 + 确认提示
2. RPE 反馈 - 输出 1-10 分选择提示
3. 伤病风险调整 - 输出调整建议 + 确认提示
4. CLI 模式 - 降级为文本输入选择

"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from src.core.base.logger import get_logger

logger = get_logger(__name__)


class ConfirmScenario(Enum):
    """确认场景类型"""

    TRAINING_PLAN = "training_plan"
    RPE_FEEDBACK = "rpe_feedback"
    INJURY_RISK_ADJUSTMENT = "injury_risk_adjustment"
    GENERIC = "generic"


class ConfirmStatus(Enum):
    """确认状态"""

    PENDING = "pending"
    CONFIRMED = "confirmed"
    REJECTED = "rejected"
    TIMEOUT = "timeout"
    CANCELLED = "cancelled"


@dataclass
class ConfirmOption:
    """确认选项"""

    key: str
    label: str
    description: str = ""
    value: Any = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "key": self.key,
            "label": self.label,
            "description": self.description,
            "value": self.value,
        }


@dataclass
class ConfirmPrompt:
    """确认提示"""

    scenario: ConfirmScenario
    title: str
    message: str
    options: list[ConfirmOption]
    default_key: str | None = None
    timeout_seconds: int = 300
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "scenario": self.scenario.value,
            "title": self.title,
            "message": self.message,
            "options": [o.to_dict() for o in self.options],
            "default_key": self.default_key,
            "timeout_seconds": self.timeout_seconds,
            "metadata": self.metadata,
        }

    def to_agent_prompt(self) -> str:
        """转换为Agent系统提示词格式

        Returns:
            str: 格式化的确认提示
        """
        lines = [
            f"【{self.title}】",
            "",
            self.message,
            "",
            "请选择：",
        ]

        for option in self.options:
            desc = f" - {option.description}" if option.description else ""
            lines.append(f"  {option.key}. {option.label}{desc}")

        if self.default_key:
            lines.append(f"\n（默认选项：{self.default_key}）")

        lines.append("\n请回复选项编号或选项名称进行确认。")

        return "\n".join(lines)

    def to_cli_prompt(self) -> str:
        """转换为CLI提示格式

        Returns:
            str: 格式化的CLI提示
        """
        lines = [
            f"\n[bold cyan]{self.title}[/bold cyan]",
            self.message,
            "",
        ]

        for option in self.options:
            desc = f" - {option.description}" if option.description else ""
            lines.append(f"  [{option.key}] {option.label}{desc}")

        return "\n".join(lines)


@dataclass
class ConfirmResult:
    """确认结果"""

    status: ConfirmStatus
    selected_key: str | None = None
    selected_option: ConfirmOption | None = None
    raw_input: str = ""
    timestamp: str = field(
        default_factory=lambda: __import__("datetime").datetime.now().isoformat()
    )
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status.value,
            "selected_key": self.selected_key,
            "selected_option": (
                self.selected_option.to_dict() if self.selected_option else None
            ),
            "raw_input": self.raw_input,
            "timestamp": self.timestamp,
            "metadata": self.metadata,
        }

    @property
    def is_confirmed(self) -> bool:
        """是否已确认"""
        return self.status == ConfirmStatus.CONFIRMED


class AskUserConfirmManager:
    """异步确认管理器

    管理所有异步确认会话，支持多轮对话中的确认状态跟踪。

    使用方式：
        manager = AskUserConfirmManager()
        prompt = manager.create_plan_confirm_prompt(plan_id, plan_summary)
        result = manager.parse_user_response(prompt, user_input)
    """

    def __init__(self) -> None:
        """初始化确认管理器"""
        self._pending_confirms: dict[str, ConfirmPrompt] = {}
        self._confirm_history: list[dict[str, Any]] = []

    def create_plan_confirm_prompt(
        self,
        plan_id: str,
        plan_summary: dict[str, Any],
    ) -> ConfirmPrompt:
        """创建训练计划确认提示

        Args:
            plan_id: 计划ID
            plan_summary: 计划摘要信息

        Returns:
            ConfirmPrompt: 确认提示
        """
        goal = plan_summary.get("goal", "未知目标")
        weeks = plan_summary.get("weeks", 0)
        volume = plan_summary.get("weekly_volume_km", 0)

        prompt = ConfirmPrompt(
            scenario=ConfirmScenario.TRAINING_PLAN,
            title="训练计划确认",
            message=(
                f"已为您生成训练计划：\n"
                f"  目标：{goal}\n"
                f"  周期：{weeks} 周\n"
                f"  周跑量：约 {volume} 公里\n\n"
                f"请确认是否采用此计划？"
            ),
            options=[
                ConfirmOption(
                    key="confirm",
                    label="确认采用",
                    description="开始使用此训练计划",
                    value=True,
                ),
                ConfirmOption(
                    key="modify",
                    label="需要调整",
                    description="告知具体调整需求",
                    value="modify",
                ),
                ConfirmOption(
                    key="cancel",
                    label="取消",
                    description="不采用此计划",
                    value=False,
                ),
            ],
            default_key="confirm",
            metadata={"plan_id": plan_id, **plan_summary},
        )

        self._pending_confirms[plan_id] = prompt
        logger.info(f"创建训练计划确认提示: plan_id={plan_id}")
        return prompt

    def create_rpe_prompt(
        self,
        session_id: str,
        session_summary: dict[str, Any] | None = None,
    ) -> ConfirmPrompt:
        """创建RPE（主观疲劳度）反馈提示

        Args:
            session_id: 训练会话ID
            session_summary: 会话摘要

        Returns:
            ConfirmPrompt: RPE选择提示
        """
        distance = session_summary.get("distance_km", 0) if session_summary else 0
        duration = session_summary.get("duration_min", 0) if session_summary else 0

        summary_text = ""
        if distance and duration:
            summary_text = f"本次训练：{distance}公里，{duration}分钟\n"

        prompt = ConfirmPrompt(
            scenario=ConfirmScenario.RPE_FEEDBACK,
            title="训练体感评分",
            message=(
                f"{summary_text}"
                f"请为本次训练的疲劳程度评分（1-10分）：\n"
                f"  1-2分：非常轻松，可以持续聊天\n"
                f"  3-4分：轻松，呼吸略微加快\n"
                f"  5-6分：中等强度，有点累但还能坚持\n"
                f"  7-8分：比较吃力，需要集中注意力\n"
                f"  9-10分：极限强度，非常吃力"
            ),
            options=[
                ConfirmOption(key="1", label="1分", description="非常轻松"),
                ConfirmOption(key="2", label="2分", description="很轻松"),
                ConfirmOption(key="3", label="3分", description="轻松"),
                ConfirmOption(key="4", label="4分", description="较轻松"),
                ConfirmOption(key="5", label="5分", description="中等"),
                ConfirmOption(key="6", label="6分", description="略累"),
                ConfirmOption(key="7", label="7分", description="较累"),
                ConfirmOption(key="8", label="8分", description="累"),
                ConfirmOption(key="9", label="9分", description="很累"),
                ConfirmOption(key="10", label="10分", description="极限"),
            ],
            default_key=None,
            metadata={"session_id": session_id},
        )

        self._pending_confirms[session_id] = prompt
        logger.info(f"创建RPE确认提示: session_id={session_id}")
        return prompt

    def create_injury_risk_prompt(
        self,
        plan_id: str,
        risk_level: str,
        suggestions: list[dict[str, Any]],
    ) -> ConfirmPrompt:
        """创建伤病风险调整确认提示

        Args:
            plan_id: 计划ID
            risk_level: 风险等级（low/medium/high）
            suggestions: 调整建议列表

        Returns:
            ConfirmPrompt: 调整确认提示
        """
        risk_text = {
            "low": "低风险 - 当前计划合理",
            "medium": "中风险 - 建议适当调整",
            "high": "高风险 - 强烈建议调整",
        }.get(risk_level, f"风险等级：{risk_level}")

        suggestion_text = "\n".join(
            f"  {i + 1}. {s.get('content', '')}（优先级：{s.get('priority', 'medium')}）"
            for i, s in enumerate(suggestions)
        )

        prompt = ConfirmPrompt(
            scenario=ConfirmScenario.INJURY_RISK_ADJUSTMENT,
            title="伤病风险调整建议",
            message=(
                f"系统检测到您的伤病风险：{risk_text}\n\n"
                f"调整建议：\n{suggestion_text}\n\n"
                f"是否接受以上调整建议？"
            ),
            options=[
                ConfirmOption(
                    key="accept",
                    label="接受建议",
                    description="按建议自动调整计划",
                    value=True,
                ),
                ConfirmOption(
                    key="partial",
                    label="部分接受",
                    description="选择部分建议执行",
                    value="partial",
                ),
                ConfirmOption(
                    key="reject",
                    label="不接受",
                    description="保持当前计划",
                    value=False,
                ),
            ],
            default_key="accept",
            metadata={
                "plan_id": plan_id,
                "risk_level": risk_level,
                "suggestions": suggestions,
            },
        )

        self._pending_confirms[plan_id] = prompt
        logger.info(f"创建伤病风险调整确认提示: plan_id={plan_id}, risk={risk_level}")
        return prompt

    def parse_user_response(
        self,
        prompt_id: str,
        user_input: str,
    ) -> ConfirmResult:
        """解析用户响应

        Args:
            prompt_id: 提示ID（通常为plan_id或session_id）
            user_input: 用户输入

        Returns:
            ConfirmResult: 确认结果
        """
        prompt = self._pending_confirms.get(prompt_id)
        if prompt is None:
            logger.warning(f"未找到待确认提示: prompt_id={prompt_id}")
            return ConfirmResult(
                status=ConfirmStatus.REJECTED,
                raw_input=user_input,
                metadata={"error": "确认已过期或不存在"},
            )

        # 标准化用户输入
        normalized_input = user_input.strip().lower()

        # 检查是否匹配选项key
        for option in prompt.options:
            if normalized_input == option.key.lower():
                result = ConfirmResult(
                    status=ConfirmStatus.CONFIRMED,
                    selected_key=option.key,
                    selected_option=option,
                    raw_input=user_input,
                )
                self._record_confirm(prompt, result)
                self._remove_pending(prompt_id)
                return result

        # 检查是否匹配选项label（模糊匹配）
        for option in prompt.options:
            if option.label.lower() in normalized_input:
                result = ConfirmResult(
                    status=ConfirmStatus.CONFIRMED,
                    selected_key=option.key,
                    selected_option=option,
                    raw_input=user_input,
                )
                self._record_confirm(prompt, result)
                self._remove_pending(prompt_id)
                return result

        # 检查确认/取消关键词（优先于选项label匹配）
        # 只有当输入不是纯选项key/label时才使用关键词匹配
        is_exact_option = False
        for option in prompt.options:
            if (
                normalized_input == option.key.lower()
                or normalized_input == option.label.lower()
            ):
                is_exact_option = True
                break

        if not is_exact_option:
            if any(
                word in normalized_input
                for word in ["确认", "确定", "是的", "ok", "yes", "y"]
            ):
                # 选择默认选项或第一个选项
                default = prompt.default_key or prompt.options[0].key
                for option in prompt.options:
                    if option.key == default:
                        result = ConfirmResult(
                            status=ConfirmStatus.CONFIRMED,
                            selected_key=option.key,
                            selected_option=option,
                            raw_input=user_input,
                            metadata={"matched_by": "keyword_confirm"},
                        )
                        self._record_confirm(prompt, result)
                        self._remove_pending(prompt_id)
                        return result

            if any(word in normalized_input for word in ["拒绝", "不", "no", "n"]):
                result = ConfirmResult(
                    status=ConfirmStatus.REJECTED,
                    raw_input=user_input,
                    metadata={"matched_by": "keyword_reject"},
                )
                self._record_confirm(prompt, result)
                self._remove_pending(prompt_id)
                return result

        # 无法解析
        logger.warning(f"无法解析用户确认输入: '{user_input}'")
        return ConfirmResult(
            status=ConfirmStatus.PENDING,
            raw_input=user_input,
            metadata={
                "error": "无法识别输入，请回复选项编号或选项名称",
                "valid_options": [o.key for o in prompt.options],
            },
        )

    def get_pending_prompt(self, prompt_id: str) -> ConfirmPrompt | None:
        """获取待确认提示

        Args:
            prompt_id: 提示ID

        Returns:
            ConfirmPrompt | None: 待确认提示
        """
        return self._pending_confirms.get(prompt_id)

    def has_pending_confirm(self, prompt_id: str) -> bool:
        """检查是否有待确认项

        Args:
            prompt_id: 提示ID

        Returns:
            bool: 是否有待确认
        """
        return prompt_id in self._pending_confirms

    def cancel_confirm(self, prompt_id: str) -> bool:
        """取消确认

        Args:
            prompt_id: 提示ID

        Returns:
            bool: 是否成功取消
        """
        if prompt_id in self._pending_confirms:
            prompt = self._pending_confirms[prompt_id]
            result = ConfirmResult(
                status=ConfirmStatus.CANCELLED,
                raw_input="",
                metadata={"cancelled_by": "user"},
            )
            self._record_confirm(prompt, result)
            self._remove_pending(prompt_id)
            logger.info(f"确认已取消: prompt_id={prompt_id}")
            return True
        return False

    def get_confirm_history(
        self,
        scenario: ConfirmScenario | None = None,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """获取确认历史

        Args:
            scenario: 按场景过滤
            limit: 返回数量限制

        Returns:
            list: 确认历史记录
        """
        history = self._confirm_history
        if scenario:
            history = [h for h in history if h.get("scenario") == scenario.value]
        return history[-limit:]

    def _record_confirm(
        self,
        prompt: ConfirmPrompt,
        result: ConfirmResult,
    ) -> None:
        """记录确认结果到历史"""
        self._confirm_history.append(
            {
                "scenario": prompt.scenario.value,
                "title": prompt.title,
                "result": result.to_dict(),
                "timestamp": result.timestamp,
            }
        )

    def _remove_pending(self, prompt_id: str) -> None:
        """移除待确认项"""
        self._pending_confirms.pop(prompt_id, None)

    def clear_history(self) -> None:
        """清空历史记录"""
        self._confirm_history.clear()
        logger.info("确认历史已清空")


class CLIConfirmHelper:
    """CLI确认辅助类

    在CLI模式下提供交互式确认输入。
    当底座不支持同步阻塞时，降级为文本输入选择。
    """

    @staticmethod
    def ask_in_cli(
        prompt: ConfirmPrompt,
        manager: AskUserConfirmManager | None = None,
    ) -> ConfirmResult:
        """在CLI中询问确认

        Args:
            prompt: 确认提示
            manager: 确认管理器实例（可选，用于测试时注入）

        Returns:
            ConfirmResult: 用户选择结果
        """
        from rich.prompt import Prompt

        console = __import__("rich.console", fromlist=["Console"]).Console()

        # 显示提示
        console.print(prompt.to_cli_prompt())

        # 构建有效选项
        valid_keys = [o.key for o in prompt.options]
        options_str = "/".join(valid_keys)

        # 使用传入的manager或创建新实例
        confirm_manager = manager or AskUserConfirmManager()
        # 使用prompt的metadata中的id作为prompt_id
        prompt_id = (
            prompt.metadata.get("plan_id") or prompt.metadata.get("session_id") or "cli"
        )

        # 循环获取有效输入
        while True:
            try:
                user_input = Prompt.ask(
                    f"请选择 [{options_str}]",
                    default=prompt.default_key or "",
                )

                if not user_input:
                    if prompt.default_key:
                        user_input = prompt.default_key
                    else:
                        console.print("[yellow]请输入有效选项[/yellow]")
                        continue

                # 解析输入
                result = confirm_manager.parse_user_response(prompt_id, user_input)

                if result.status == ConfirmStatus.PENDING:
                    console.print(
                        f"[yellow]{result.metadata.get('error', '无效输入')}[/yellow]"
                    )
                    continue

                return result

            except KeyboardInterrupt:
                console.print("\n[yellow]已取消[/yellow]")
                return ConfirmResult(
                    status=ConfirmStatus.CANCELLED,
                    raw_input="",
                )
            except EOFError:
                return ConfirmResult(
                    status=ConfirmStatus.CANCELLED,
                    raw_input="",
                )

    @staticmethod
    def ask_rpe_in_cli(session_summary: dict[str, Any] | None = None) -> int | None:
        """在CLI中询问RPE评分

        Args:
            session_summary: 会话摘要

        Returns:
            int | None: RPE评分（1-10），取消返回None
        """
        manager = AskUserConfirmManager()
        session_id = (
            session_summary.get("session_id", "cli") if session_summary else "cli"
        )
        prompt = manager.create_rpe_prompt(session_id, session_summary)

        result = CLIConfirmHelper.ask_in_cli(prompt)

        if result.is_confirmed and result.selected_option:
            try:
                return int(result.selected_option.key)
            except ValueError:
                return None
        return None


# 便捷函数


def create_plan_confirm_prompt(
    plan_id: str,
    plan_summary: dict[str, Any],
) -> ConfirmPrompt:
    """创建训练计划确认提示（便捷函数）"""
    manager = AskUserConfirmManager()
    return manager.create_plan_confirm_prompt(plan_id, plan_summary)


def create_rpe_prompt(
    session_id: str,
    session_summary: dict[str, Any] | None = None,
) -> ConfirmPrompt:
    """创建RPE反馈提示（便捷函数）"""
    manager = AskUserConfirmManager()
    return manager.create_rpe_prompt(session_id, session_summary)


def create_injury_risk_prompt(
    plan_id: str,
    risk_level: str,
    suggestions: list[dict[str, Any]],
) -> ConfirmPrompt:
    """创建伤病风险调整提示（便捷函数）"""
    manager = AskUserConfirmManager()
    return manager.create_injury_risk_prompt(plan_id, risk_level, suggestions)


def parse_user_response(prompt_id: str, user_input: str) -> ConfirmResult:
    """解析用户响应（便捷函数）"""
    manager = AskUserConfirmManager()
    return manager.parse_user_response(prompt_id, user_input)
