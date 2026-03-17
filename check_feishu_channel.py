import inspect
from nanobot.channels import feishu

print("=== nanobot.channels.feishu 模块 ===")
print("导出的类和函数:")
for name in dir(feishu):
    if not name.startswith('_'):
        obj = getattr(feishu, name)
        if inspect.isclass(obj):
            print(f"  类: {name}")
            # 打印类的方法
            methods = [m for m in dir(obj) if not m.startswith('_') and callable(getattr(obj, m))]
            if methods:
                print(f"    方法: {methods}")
        elif inspect.isfunction(obj):
            print(f"  函数: {name}")
            print(f"    签名: {inspect.signature(obj)}")
