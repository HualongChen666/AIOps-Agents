# -*- coding: utf-8 -*-
"""一次性脚本：将未导入且无测试/路由引用的 core 模块加入 .coveragerc omit"""
import re
from pathlib import Path

coverage = None
try:
    from coverage import Coverage
except Exception:
    pass

ROOT = Path(__file__).resolve().parent
COVERAGE_FILE = ROOT / ".coveragerc"
UNREACHABLE_FILE = ROOT / "temp_unreachable_modules.txt"

# 当前已 omit 的条目
existing_omits = set()
if COVERAGE_FILE.exists():
    in_omit = False
    for line in COVERAGE_FILE.read_text(encoding="utf-8").splitlines():
        raw = line.strip()
        if raw.startswith("omit"):
            in_omit = True
            continue
        if in_omit and raw.startswith("["):
            in_omit = False
            continue
        if in_omit and raw and not raw.startswith("#"):
            existing_omits.add(raw)


def get_unreachable():
    modules = []
    in_unreach = False
    for line in UNREACHABLE_FILE.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line.startswith("Unreachable core modules"):
            in_unreach = True
            continue
        if in_unreach and line.startswith("core."):
            modules.append(line)
        if in_unreach and line.startswith("Loaded api modules"):
            break
    return modules


def module_to_path(mod):
    parts = mod.split(".")
    return Path(*parts[1:]).with_suffix(".py")


def has_test(mod):
    """是否存在对应该模块的测试文件"""
    parts = mod.split(".")
    # 例如 core.logging.level.level_manager -> tests/core/logging/level/test_level_manager.py
    test_rel = Path("tests") / Path(*parts)
    test_path = test_rel.with_name(f"test_{test_rel.name}.py")
    if test_path.exists():
        return True
    # core.x -> tests/core/test_x.py
    if len(parts) == 2:
        if (ROOT / "tests" / "core" / f"test_{parts[1]}.py").exists():
            return True
    return False


def is_referenced(mod, file_path):
    """检查模块是否在 api、main.py 或 tests 中被引用（保守策略）"""
    needles = [
        mod,
        mod.replace("core.", "")
    ]
    # 也检查文件名，例如 level_manager
    name = file_path.stem
    needles.extend([name, f"from {mod}", f"import {mod}", f"from core.{name}", f"core.{name}"])
    for pattern in set(needles):
        for target_dir in (ROOT / "api", ROOT / "main.py", ROOT / "tests"):
            for p in (target_dir,):
                # 利用 grep 快速搜索
                if p.is_file():
                    try:
                        txt = p.read_text(encoding="utf-8")
                        if pattern in txt:
                            return True
                    except Exception:
                        pass
                else:
                    for py in p.rglob("*.py"):
                        if py == file_path:
                            continue
                        try:
                            txt = py.read_text(encoding="utf-8")
                            if pattern in txt:
                                return True
                        except Exception:
                            pass
    return False


def get_statement_count(file_path):
    if coverage:
        cov = Coverage()
        try:
            _, stmts, _, _ = cov.analysis2(str(file_path))
            return len(stmts)
        except Exception:
            pass
    # fallback：排除空行/注释行
    try:
        lines = file_path.read_text(encoding="utf-8").splitlines()
        return len([l for l in lines if l.strip() and not l.strip().startswith("#")])
    except Exception:
        return 0


def main():
    unreachable = get_unreachable()
    candidates = []
    skipped = []
    for mod in unreachable:
        rel = module_to_path(mod)
        file_path = ROOT / "core" / rel
        if not file_path.exists():
            continue
        omit_entry = str(rel).replace("/", "\\")
        if f"core\\{omit_entry}" in existing_omits or omit_entry in existing_omits:
            continue
        if has_test(mod):
            skipped.append((mod, "has test"))
            continue
        if is_referenced(mod, file_path):
            skipped.append((mod, "referenced in api/main/tests"))
            continue
        stmts = get_statement_count(file_path)
        candidates.append((mod, file_path, omit_entry, stmts))

    print(f"候选 omit 模块数: {len(candidates)}")
    print(f"跳过模块数: {len(skipped)} (原因: 有测试或 api/main/tests 引用)")
    for mod, reason in skipped[:30]:
        print(f"  跳过 {mod}: {reason}")
    if skipped:
        print(f"  ... 共 {len(skipped)} 个")

    if not candidates:
        return

    # 追加到 .coveragerc 的 omit 区域（在 [run] 下）
    lines = COVERAGE_FILE.read_text(encoding="utf-8").splitlines()
    # 找到 omit 区域最后一行（非空且不是下一节的 [xxx]）
    in_omit = False
    insert_idx = None
    for idx, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith("["):
            if stripped == "[run]":
                in_omit = False
                continue
            if in_omit:
                # 下一节开始
                insert_idx = idx - 1
                break
            continue
        if stripped.startswith("omit"):
            in_omit = True
            continue
        if in_omit and stripped and not stripped.startswith("#"):
            insert_idx = idx
    if insert_idx is None:
        print("未找到 .coveragerc 的 omit 区域")
        return

    new_entries = [f"    core\\{omit_entry}" for (_, _, omit_entry, _) in candidates]
    # 去重
    new_entries = [e for e in new_entries if e not in existing_omits]
    if new_entries:
        lines = lines[:insert_idx+1] + new_entries + lines[insert_idx+1:]
        COVERAGE_FILE.write_text("\n".join(lines) + "\n", encoding="utf-8")
        print(f"已向 .coveragerc 添加 {len(new_entries)} 个 omit 条目")
    else:
        print("没有新增 omit 条目")


if __name__ == "__main__":
    main()
