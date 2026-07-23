#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Statically compute which core/api modules are reachable from main.py / api routers.
Outputs a list of file paths that can be added to .coveragerc omit section.
"""

import ast
import os
import sys
from collections import defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]


def module_name_from_path(path: Path) -> str:
    rel = path.relative_to(REPO).with_suffix("")
    parts = rel.parts
    if parts[0] == "core" or parts[0] == "api":
        return ".".join(parts)
    if parts[0] == "main":
        return "main"
    return ".".join(parts)


def resolve_relative(level: int, module: str | None, current_module: str) -> list[str]:
    parts = current_module.split(".")
    if level > len(parts):
        return []
    base = parts[: len(parts) - level]
    if module:
        base += module.split(".")
    return [".".join(base)] if base else []


def resolve_import(node: ast.AST, current_module: str, existing_modules: set[str]) -> list[str]:
    deps = []
    if isinstance(node, ast.Import):
        for alias in node.names:
            name = alias.name
            if name.startswith("core.") or name.startswith("api.") or name == "main":
                deps.append(name)
            # also accept package root
            elif name in existing_modules:
                deps.append(name)
    elif isinstance(node, ast.ImportFrom):
        level = node.level
        module = node.module
        if level:
            base = resolve_relative(level, module, current_module)
        elif module:
            base = [module]
        else:
            return deps
        for b in base:
            # e.g. from core import notify_engine -> try core.notify_engine
            for alias in node.names:
                candidate = f"{b}.{alias.name}"
                if candidate in existing_modules:
                    deps.append(candidate)
                elif b in existing_modules:
                    deps.append(b)
    return deps


def build_graph(root_dirs: list[Path]) -> dict[str, set[str]]:
    graph = defaultdict(set)
    existing_modules = set()
    py_files: list[tuple[Path, str]] = []
    for d in root_dirs:
        for py in d.rglob("*.py"):
            if py.name.startswith("test_"):
                continue
            mod = module_name_from_path(py)
            existing_modules.add(mod)
            py_files.append((py, mod))

    # Also parse repo-level main.py if present
    main_py = REPO / "main.py"
    if main_py.exists():
        py_files.append((main_py, "main"))

    for py, mod in py_files:
        try:
            tree = ast.parse(py.read_text(encoding="utf-8"))
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                for dep in resolve_import(node, mod, existing_modules):
                    if dep != mod:
                        graph[mod].add(dep)
    return graph, existing_modules


def reachable_from(graph: dict[str, set[str]], seeds: set[str]) -> set[str]:
    seen = set()
    stack = list(seeds)
    while stack:
        node = stack.pop()
        if node in seen:
            continue
        seen.add(node)
        for nxt in graph.get(node, set()):
            if nxt not in seen:
                stack.append(nxt)
    return seen


def main() -> int:
    graph, modules = build_graph([REPO / "core", REPO / "api"])
    # Add main.py itself
    main_mods = {"main"}
    # seeds = everything main imports directly or transitively
    main_path = REPO / "main.py"
    if main_path.exists():
        main_mods.add("main")
    reachable = reachable_from(graph, main_mods)

    # also include anything directly imported by api modules (main should, but be safe)
    api_modules = {m for m in modules if m.startswith("api.")}
    reachable |= reachable_from(graph, api_modules)

    core_api_modules = {m for m in modules if m.startswith("core.") or m.startswith("api.")}
    unreachable = sorted(core_api_modules - reachable)

    unreachable_files = []
    for mod in unreachable:
        # convert module name back to path
        rel = mod.replace(".", os.sep) + ".py"
        path = REPO / rel
        if path.exists():
            unreachable_files.append(str(rel))

    output_path = REPO / "unreachable_modules_latest.txt"
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(f"Unreachable core/api modules: {len(unreachable_files)}\n")
        for p in unreachable_files:
            f.write(f"{p}\n")
    print(f"Unreachable core/api modules: {len(unreachable_files)}")
    for p in unreachable_files:
        print(p)
    return 0


if __name__ == "__main__":
    sys.exit(main())
