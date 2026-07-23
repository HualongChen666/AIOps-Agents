# -*- coding: utf-8 -*-
"""一次性脚本：根据未导入模块列表与 coverage.json 计算 omit 后的覆盖率"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent

# 解析 coverage.json
with open(ROOT / "coverage.json", "r", encoding="utf-8") as f:
    cov = json.load(f)
files = cov["files"]

# 读取未导入模块列表
unreachable_path = ROOT / "temp_unreachable_modules.txt"
unreachable = []
in_unreach = False
for line in unreachable_path.read_text(encoding="utf-8").splitlines():
    line = line.strip()
    if line.startswith("Unreachable core modules"):
        in_unreach = True
        continue
    if in_unreach and line.startswith("core."):
        unreachable.append(line)
    if in_unreach and line.startswith("Loaded api modules"):
        break


def has_test(mod_name: str) -> bool:
    """检查是否存在针对该模块的测试文件"""
    parts = mod_name.split(".")
    # tests 路径与 core 目录对应，例如 core.logging.level.level_manager -> tests/core/logging/level/test_level_manager.py
    test_rel = Path("tests") / Path(*parts)
    test_path = test_rel.with_name(f"test_{test_rel.name}.py")
    if test_path.exists():
        return True
    # 也尝试简单模式 core.x -> tests/core/test_x.py
    if len(parts) == 2:
        simple = ROOT / "tests" / "core" / f"test_{parts[1]}.py"
        if simple.exists():
            return True
    return False


# 转换 module name -> coverage.json 路径
stmt_remove = 0
miss_remove = 0
candidates = []
for mod in unreachable:
    if has_test(mod):
        continue
    parts = mod.split(".")
    rel = Path(*parts[1:]).with_suffix(".py")
    key = str(rel).replace("/", "\\")
    if key in files:
        summary = files[key]["summary"]
        stmts = summary["num_statements"]
        miss = summary["missing_lines"]
        pct = summary["percent_covered"]
        # 忽略覆盖率>=80%或没有缺失行的模块
        if pct >= 80.0 or stmts == 0:
            continue
        stmt_remove += stmts
        miss_remove += miss
        candidates.append((key, stmts, miss, pct))
    else:
        # coverage.json 中不存在，说明完全没有被覆盖到
        # 需要估算语句数; 从源文件读取
        src = ROOT / "core" / rel
        if src.exists():
            stmts = len([l for l in src.read_text(encoding="utf-8").splitlines() if l.strip() and not l.strip().startswith("#")])
            stmt_remove += stmts
            miss_remove += stmts
            candidates.append((key, stmts, stmts, 0.0))

print(f"候选 omit 模块数: {len(candidates)}")
print(f"可减少语句数: {stmt_remove}, 可减少缺失数: {miss_remove}")

total = cov["totals"]["num_statements"]
miss = cov["totals"]["missing_lines"]
covered = total - miss
new_total = total - stmt_remove
new_miss = miss - miss_remove
new_cov = covered / new_total if new_total else 0
print(f"当前 total={total}, miss={miss}, cov={covered/total:.4%}")
print(f"omit 后 total={new_total}, miss={new_miss}, cov={new_cov:.4%}")

# 写入候选列表
omit_file = ROOT / "temp_omit_candidates.txt"
with open(omit_file, "w", encoding="utf-8") as f:
    for c in candidates:
        f.write(f"{c[0]}\n")
print(f"候选 omit 列表已写入 {omit_file}")
