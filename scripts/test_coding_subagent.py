# -*- coding: utf-8 -*-
"""临时测试 CodingSubAgent 和 CodingToolRegistry。"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.agent.coding_subagent import CodingSubAgent, create_coding_subagent_dispatcher


def main():
    # 单个子代理测试
    agent = CodingSubAgent(agent_id="test-coding")
    result = agent.run(
        goal="echo test",
        context={
            "tool": "bash",
            "params": {"command": ["python", "-c", "print('coding_subagent works')"]},
        },
        available_tools=["bash"],
    )
    print("single result:", result.status, result.result)

    # 调度器批量测试
    dispatcher = create_coding_subagent_dispatcher(max_workers=4)
    tasks = [
        {
            "goal": "task1",
            "context": {
                "tool": "bash",
                "params": {"command": ["python", "-c", "print('task1 ok')"]},
            },
            "role": "worker",
        },
        {
            "goal": "task2",
            "context": {
                "tool": "bash",
                "params": {"command": ["python", "-c", "print('task2 ok')"]},
            },
            "role": "worker",
        },
        {
            "goal": "task3",
            "context": {
                "tool": "bash",
                "params": {"command": ["python", "-c", "print('task3 ok')"]},
            },
            "role": "worker",
        },
    ]
    results = dispatcher.dispatch_batch(tasks)
    dispatcher.shutdown(wait=True)
    for r in results:
        print("batch result:", r.status, r.result)


if __name__ == "__main__":
    main()
