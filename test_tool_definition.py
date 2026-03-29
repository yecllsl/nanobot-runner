"""测试工具定义是否正确传递给 LLM"""
import asyncio
import json
from pathlib import Path
from nanobot.config.loader import load_config, get_data_dir
from nanobot.agent.tools import ToolRegistry
from nanobot.cli.commands import _make_provider
from src.agents.tools import RunnerTools, create_tools
from src.core.storage import StorageManager


async def test_tool_definitions():
    """测试工具定义"""
    config = load_config()
    workspace = get_data_dir()
    
    storage = StorageManager()
    runner_tools = RunnerTools(storage)
    
    registry = ToolRegistry()
    for tool in create_tools(runner_tools):
        registry.register(tool)
    
    tools = registry.get_definitions()
    
    print("=" * 80)
    print("工具定义数量:", len(tools))
    print("=" * 80)
    
    for tool in tools:
        print(f"\n工具名称: {tool['function']['name']}")
        print(f"工具描述: {tool['function']['description'][:100]}...")
        print(f"参数定义: {json.dumps(tool['function']['parameters'], indent=2, ensure_ascii=False)}")
    
    print("\n" + "=" * 80)
    print("测试 LLM 调用")
    print("=" * 80)
    
    provider = _make_provider(config)
    
    messages = [
        {"role": "system", "content": "你是一个跑步数据助手。"},
        {"role": "user", "content": "/stats"}
    ]
    
    response = await provider.chat(
        messages=messages,
        tools=tools,
        model=config.agents.defaults.model,
        temperature=config.agents.defaults.temperature,
        max_tokens=config.agents.defaults.max_tokens,
    )
    
    print(f"\n响应内容: {response.content}")
    print(f"工具调用数量: {len(response.tool_calls)}")
    
    if response.tool_calls:
        for tc in response.tool_calls:
            print(f"  - 工具: {tc.name}, 参数: {tc.arguments}")
    else:
        print("  ⚠️ 没有工具调用！")
    
    print(f"\n完成原因: {response.finish_reason}")


if __name__ == "__main__":
    asyncio.run(test_tool_definitions())
