# -*- coding: utf-8 -*-
"""并行分发 14.1-17.8 共 32 个 SubAgent 子任务。"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Dict, List

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from core.agent.coding_subagent import create_coding_subagent_dispatcher

TASK_IDS = [f"{m}.{i}" for m in range(14, 18) for i in range(1, 9)]


def build_tasks() -> List[Dict[str, Any]]:
    """构建 32 个 SubAgent 任务。"""
    tasks = []
    for tid in TASK_IDS:
        tasks.append(
            {
                "goal": f"execute task {tid}",
                "context": {
                    "tool": "bash",
                    "params": {
                        "command": [
                            "python",
                            "scripts/task_verifier.py",
                            "--task",
                            tid,
                        ]
                    },
                },
                "available_tools": ["bash"],
                "role": "worker",
                "agent_id": f"agent_{tid.replace('.', '_')}",
            }
        )
    return tasks


def main() -> None:
    dispatcher = create_coding_subagent_dispatcher(max_workers=6)
    tasks = build_tasks()
    results = dispatcher.dispatch_batch(tasks)
    dispatcher.shutdown(wait=True)

    print("\n=== SubAgent 任务结果 ===\n")
    failed = []
    for tid, result in zip(TASK_IDS, results):
        status = result.status
        if status == "completed" and result.result:
            stdout = result.result.get("stdout", "")
            first_line = stdout.splitlines()[0] if stdout else "OK"
            print(f"{tid}: {status} -> {first_line}")
        else:
            print(f"{tid}: {status} -> {result.error or 'failed'}")
            failed.append(tid)

    print("\n=== 汇总 ===")
    print(f"总任务: {len(TASK_IDS)}")
    print(f"失败/未通过: {len(failed)} ({', '.join(failed) if failed else '无'})")


if __name__ == "__main__":
    main()
