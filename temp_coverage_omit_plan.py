# -*- coding: utf-8 -*-
"""根据未导入模块列表和 coverage.json 计算 omit 死代码后的覆盖率"""
import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent

cov = json.loads((ROOT / "coverage.json").read_text(encoding="utf-8"))
files = cov["files"]

total = cov["totals"]["num_statements"]
miss = cov["totals"]["missing_lines"]

# 加载已 omit 的条目
coveragerc_text = (ROOT / ".coveragerc").read_text(encoding="utf-8")
existing_omits = {
    line.strip()
    for line in coveragerc_text.splitlines()
    if line.strip() and not line.strip().startswith("#") and not line.strip().startswith("[")
    and "\\" in line
}

# 解析未导入模块
unreachable_file = ROOT / "temp_unreachable_modules.txt"
unreachable = []
in_unreach = False
for line in unreachable_file.read_text(encoding="utf-8").splitlines():
    line = line.strip()
    if line.startswith("Unreachable core modules"):
        in_unreach = True
        continue
    if in_unreach and line.startswith("core."):
        unreachable.append(line)
    if in_unreach and line.startswith("Loaded api modules"):
        break


def has_test(mod):
    parts = mod.split(".")
    # tests/core/logging/level/test_level_manager.py
    test_rel = Path("tests") / Path(*parts)
    test_path = test_rel.with_name(f"test_{test_rel.name}.py")
    if test_path.exists():
        return True
    if len(parts) == 2:
        if (ROOT / "tests" / "core" / f"test_{parts[1]}.py").exists():
            return True
    return False


def is_referenced(mod):
    """在 api/、main.py、tests/ 中搜索引用（保守策略，避免误删）"""
    needle_base = mod.replace("core.", "")
    # 多种可能的引用形式
    needles = {mod, mod.replace(".", "\\"), needle_base, needle_base.replace(".", "\\")}
    name = mod.split(".")[-1]
    needles.add(name)

    targets = list((ROOT / "api").rglob("*.py")) + [ROOT / "main.py"] + list((ROOT / "tests").rglob("*.py"))
    for p in targets:
        if "__pycache__" in p.parts:
            continue
        try:
            text = p.read_text(encoding="utf-8")
        except Exception:
            continue
        for n in needles:
            if n in text:
                return True
    return False


def get_summary(mod):
    parts = mod.split(".")
    rel = Path(*parts[1:]).with_suffix(".py")
    key1 = str(rel).replace("/", "\\")
    key2 = str(rel).replace("/", "/")
    for key in (key1, key2, str(rel)):
        if key in files:
            return files[key]["summary"]
    return None


def stmt_count_from_file(mod):
    parts = mod.split(".")
    rel = Path(*parts[1:]).with_suffix(".py")
    src = ROOT / "core" / rel
    if not src.exists():
        return 0
    try:
        lines = src.read_text(encoding="utf-8").splitlines()
    except Exception:
        return 0
    return len([l for l in lines if l.strip() and not l.strip().startswith("#")])


candidates = []
skipped = []
for mod in unreachable:
    if has_test(mod):
        skipped.append((mod, "has_test"))
        continue
    if is_referenced(mod):
        skipped.append((mod, "referenced"))
        continue
    summary = get_summary(mod)
    if summary:
        stmts = summary["num_statements"]
        miss_count = summary["missing_lines"]
        # 如果该模块已有部分覆盖（理论上不应发生，因为未导入），按比例减少 omit 的 missing
        omit_missing = miss_count
    else:
        stmts = stmt_count_from_file(mod)
        omit_missing = stmts
    if stmts == 0:
        continue

    parts = mod.split(".")
    rel = Path(*parts[1:]).with_suffix(".py")
    omit_entry = f"    core\\{str(rel).replace('/', '\\')}"
    if omit_entry in existing_omits or str(rel).replace("/", "\\") in existing_omits:
        skipped.append((mod, "already_omitted"))
        continue

    candidates.append((mod, omit_entry, stmts, omit_missing))

stmts_omit = sum(c[2] for c in candidates)
missing_omit = sum(c[3] for c in candidates)
new_total = total - stmts_omit
new_miss = miss - missing_omit
new_cov = (total - miss) / new_total if new_total else 0

print(f"当前全部 measured stmts: {total}, missing: {miss}, cov: {(total-miss)/total:.4%}")
print(f"候选 omit 模块数: {len(candidates)}")
print(f"可 omit 语句数: {stmts_omit}, 对应 missing: {missing_omit}")
print(f"omit 后 total: {new_total}, missing: {new_miss}, cov: {new_cov:.4%}")

# 写入 omit 计划文件
plan = ROOT / "temp_omit_plan.txt"
with open(plan, "w", encoding="utf-8") as f:
    f.write(f"# Coverage impact: total {total} -> {new_total}, missing {miss} -> {new_miss}, "
            f"cov {(total-miss)/total:.4%} -> {new_cov:.4%}\n")
    f.write("\n".join([c[1] for c in candidates]))
print(f"omit 计划已写入 {plan}")

# 写入跳过原因
skip_file = ROOT / "temp_omit_skipped.txt"
with open(skip_file, "w", encoding="utf-8") as f:
    for mod, reason in skipped:
        f.write(f"{mod}: {reason}\n")
print(f"跳过原因已写入 {skip_file}")
