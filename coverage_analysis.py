import xml.etree.ElementTree as ET

# 解析 coverage.xml
tree = ET.parse('coverage.xml')
root = tree.getroot()

print('=== 代码覆盖率分析 ===')
print(f'总体覆盖率: {float(root.get("line-rate")):.1%}')

# 分析各模块覆盖率
modules = {}
for package in root.findall('.//package'):
    name = package.get('name')
    line_rate = float(package.get('line-rate'))
    modules[name] = line_rate
    
# 按模块类型分类
core_modules = {k: v for k, v in modules.items() if k.startswith('src.core')}
agent_modules = {k: v for k, v in modules.items() if k.startswith('src.agents')}
cli_modules = {k: v for k, v in modules.items() if k.startswith('src.cli')}

print(f'\nCore 模块数量: {len(core_modules)}')
print(f'Agents 模块数量: {len(agent_modules)}')
print(f'CLI 模块数量: {len(cli_modules)}')

# 计算平均覆盖率
core_avg = sum(core_modules.values()) / len(core_modules) if core_modules else 0
agent_avg = sum(agent_modules.values()) / len(agent_modules) if agent_modules else 0
cli_avg = sum(cli_modules.values()) / len(cli_modules) if cli_modules else 0

print(f'\nCore 平均覆盖率: {core_avg:.1%}')
print(f'Agents 平均覆盖率: {agent_avg:.1%}')
print(f'CLI 平均覆盖率: {cli_avg:.1%}')

# 检查门禁要求
requirements = {
    'core': {'min': 0.8, 'actual': core_avg, 'passed': core_avg >= 0.8},
    'agents': {'min': 0.7, 'actual': agent_avg, 'passed': agent_avg >= 0.7},
    'cli': {'min': 0.6, 'actual': cli_avg, 'passed': cli_avg >= 0.6}
}

print('\n=== 门禁检查结果 ===')
for module, req in requirements.items():
    status = '✅ 通过' if req['passed'] else '❌ 不通过'
    print(f'{module.upper()}: {req["actual"]:.1%} (要求≥{req["min"]:.0%}) - {status}')

# 检查覆盖率低于门禁的模块
print('\n=== 低覆盖率模块警告 ===')
for name, coverage in modules.items():
    if coverage < 0.8 and name.startswith('src.core'):
        print(f'⚠️  Core模块 {name}: {coverage:.1%} < 80%')
    elif coverage < 0.7 and name.startswith('src.agents'):
        print(f'⚠️  Agents模块 {name}: {coverage:.1%} < 70%')
    elif coverage < 0.6 and name.startswith('src.cli'):
        print(f'⚠️  CLI模块 {name}: {coverage:.1%} < 60%')