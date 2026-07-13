"""nanobot API 契约测试 - 锁定 RunFlowAgent 依赖的公开 API 行为

基于 nanobot-ai 0.2.2 实际 API 调研结果编写。
当 nanobot 升级导致 API 破坏性变更时，这些测试会先失败，提供早期预警。
"""

import inspect


def test_agent_loop_constructor_signature():
    """验证 AgentLoop 构造函数签名"""
    from nanobot.agent import AgentLoop

    sig = inspect.signature(AgentLoop.__init__)
    params = list(sig.parameters.keys())
    # 锁定关键参数存在
    assert "bus" in params
    assert "provider" in params
    assert "workspace" in params
    assert "model" in params


def test_agent_loop_public_methods():
    """验证 AgentLoop 公开方法存在"""
    from nanobot.agent import AgentLoop

    assert hasattr(AgentLoop, "run")
    assert hasattr(AgentLoop, "process_direct")
    assert hasattr(AgentLoop, "close_mcp")
    assert hasattr(AgentLoop, "stop")
    # 0.2.2 新增
    assert hasattr(AgentLoop, "submit_cron_turn")


def test_agent_hook_interface():
    """验证 AgentHook 接口"""
    from nanobot.agent.hook import AgentHook

    assert hasattr(AgentHook, "before_iteration")
    assert hasattr(AgentHook, "after_iteration")
    assert hasattr(AgentHook, "before_execute_tools")


def test_tool_base_interface():
    """验证 Tool 基类接口"""
    from nanobot.agent.tools.base import Tool

    assert hasattr(Tool, "name")
    assert hasattr(Tool, "description")
    assert hasattr(Tool, "parameters")
    assert hasattr(Tool, "execute")
    assert hasattr(Tool, "cast_params")
    assert hasattr(Tool, "to_schema")


def test_config_schema_fields():
    """验证 Config Schema 字段

    使用实例检查，因 Pydantic/dataclass 字段是描述符，
    hasattr 在类上返回 False，在实例上返回 True。
    """
    from nanobot.config.schema import AgentsConfig, Config, ProvidersConfig

    config = Config()
    assert hasattr(config, "agents")
    assert hasattr(config, "providers")
    assert hasattr(config, "transcription")  # 0.2.2 新增
    # 验证类型可实例化
    AgentsConfig()
    ProvidersConfig()


def test_message_bus_interface():
    """验证 MessageBus 事件接口"""
    from nanobot.bus.events import InboundMessage, OutboundMessage

    # InboundMessage 有 session_key
    assert hasattr(InboundMessage, "session_key")
    # OutboundMessage 用 channel/chat_id 标识投递目标（非 session_key）
    outbound = OutboundMessage(channel="test", chat_id="123", content="hi")
    assert hasattr(outbound, "channel")
    assert hasattr(outbound, "chat_id")


def test_cron_service_interface():
    """验证 CronService 接口"""
    from nanobot.cron.service import CronService

    sig = inspect.signature(CronService.__init__)
    assert "store_path" in sig.parameters
    assert "on_job" in sig.parameters


def test_sdk_interface():
    """验证 SDK 接口（0.2.2 新增）

    注意：类名是 Nanobot（非 NanobotSDK）。
    通过 from_config() classmethod 创建，支持 async with 上下文。
    """
    from nanobot.nanobot import Nanobot

    assert hasattr(Nanobot, "stream")
    assert hasattr(Nanobot, "run")
    assert hasattr(Nanobot, "from_config")
    assert hasattr(Nanobot, "__aenter__")
    assert hasattr(Nanobot, "__aexit__")


def test_runtime_event_publisher_interface():
    """验证 RuntimeEventPublisher 接口（0.2.2 新增）

    注意：实际方法不是 publish/subscribe，而是事件回调方法。
    RunFlowAgent 的 RuntimeEventHook 通过 AgentHook 接口订阅事件，
    不直接依赖 RuntimeEventPublisher 的方法。
    """
    from nanobot.bus.runtime_events import RuntimeEventPublisher

    # 验证关键事件回调方法存在
    assert hasattr(RuntimeEventPublisher, "turn_completed")
    assert hasattr(RuntimeEventPublisher, "session_turn_started")
    assert hasattr(RuntimeEventPublisher, "run_status_changed")


def test_provider_registry_interface():
    """验证 Provider Registry 接口（0.2.2 新增）

    RunFlowAgent 的 DynamicProviderRegistry 依赖 create_dynamic_spec 和 PROVIDERS。
    """
    from nanobot.providers.registry import PROVIDERS, ProviderSpec, create_dynamic_spec

    # PROVIDERS 是非空列表
    assert len(PROVIDERS) > 0
    # create_dynamic_spec 接受 name 参数，会规范化连字符为下划线
    spec = create_dynamic_spec("test_custom")
    assert isinstance(spec, ProviderSpec)
    assert spec.name == "test_custom"


def test_cron_session_delivery_interface():
    """验证 Cron 会话投递接口（0.2.2 新增）

    RunFlowAgent 的 CronCallbackHandler 依赖 origin_delivery_context 函数。
    """
    from nanobot.cron.session_delivery import origin_delivery_context
    from nanobot.cron.types import CronPayload

    # CronPayload 支持会话绑定字段
    payload = CronPayload(
        kind="agent_turn",
        message="test",
        session_key="test:session",
        origin_channel="feishu",
        origin_chat_id="chat_001",
    )
    assert hasattr(payload, "session_key")
    assert hasattr(payload, "origin_channel")
    assert hasattr(payload, "origin_chat_id")
    # origin_delivery_context 是可调用函数
    assert callable(origin_delivery_context)
