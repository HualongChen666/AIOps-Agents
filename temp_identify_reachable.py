# -*- coding: utf-8 -*-
"""一次性脚本：识别 main.py / api routers 实际导入的 core/api 模块"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent

# 导入主入口和 routers，尽量收集已加载模块
try:
    import main  # noqa: F401
except Exception as e:
    print(f"import main failed: {e}")

try:
    import api  # noqa: F401
except Exception as e:
    print(f"import api failed: {e}")

# 尝试导入所有 routers
api_dir = ROOT / "api"
for p in api_dir.glob("*.py"):
    if p.name.startswith("_"):
        continue
    mod_name = f"api.{p.stem}"
    try:
        __import__(mod_name)
    except Exception as e:
        pass

loaded = set(sys.modules.keys())

core_dir = ROOT / "core"
api_dir = ROOT / "api"

def collect_modules(pkg_dir, pkg_name):
    modules = {}
    for p in pkg_dir.rglob("*.py"):
        if p.name.startswith("_"):
            continue
        rel = p.relative_to(pkg_dir)
        parts = rel.with_suffix("").parts
        mod_name = f"{pkg_name}.{".".join(parts)}"
        modules[mod_name] = rel.as_posix()
    return modules

core_modules = collect_modules(core_dir, "core")
api_modules = collect_modules(api_dir, "api")

loaded_core = {m for m in loaded if m.startswith("core.")}
loaded_api = {m for m in loaded if m.startswith("api.")}

unreachable_core = sorted(set(core_modules) - loaded_core)
unreachable_api = sorted(set(api_modules) - loaded_api)

out = ROOT / "temp_unreachable_modules.txt"
lines = [f"Loaded core modules: {len(loaded_core)}"]
lines.append(f"Total core modules: {len(core_modules)}")
lines.append(f"Unreachable core modules ({len(unreachable_core)}):")
lines.extend(unreachable_core)
lines.append("")
lines.append(f"Loaded api modules: {len(loaded_api)}")
lines.append(f"Total api modules: {len(api_modules)}")
lines.append(f"Unreachable api modules ({len(unreachable_api)}):")
lines.extend(unreachable_api)
out.write_text("\n".join(lines), encoding="utf-8")
print(f"Saved unreachable modules to {out}")
