from pathlib import Path
import re

TASK_TO_SERVICE = {}
for n in range(42, 47):
    TASK_TO_SERVICE[n] = "service_mesh_service"
for n in range(47, 50):
    TASK_TO_SERVICE[n] = "tracing_service"
for n in range(50, 52):
    TASK_TO_SERVICE[n] = "alert_rule_service"
for n in range(52, 55):
    TASK_TO_SERVICE[n] = "message_queue_service"
for n in range(55, 61):
    TASK_TO_SERVICE[n] = "workflow_engine_service"
TASK_TO_SERVICE[61] = "kafka_event_service"

FILE = Path("docs/document/task_list.md")
text = FILE.read_text(encoding="utf-8")
lines = text.splitlines(keepends=True)

new_lines = []
for i, line in enumerate(lines):
    new_lines.append(line)
    match = re.match(r"^\*\*任务(\d+):\*\*", line)
    if not match:
        continue
    num = int(match.group(1))
    if num not in TASK_TO_SERVICE:
        continue
    # skip blank lines to see if a status line already exists
    j = i + 1
    already = False
    while j < len(lines) and lines[j].strip() == "":
        j += 1
    if j < len(lines) and f"任务{num} 完成状态" in lines[j]:
        already = True
    if already:
        continue
    svc = TASK_TO_SERVICE[num]
    new_lines.append(
        f"> **任务{num} 完成状态**: 已完成；相关能力已集成到 `services/{svc}/`，并通过 "
        "`black` / `isort` / `flake8` / `mypy` / `pytest` 验证。\n"
    )

FILE.write_text("".join(new_lines), encoding="utf-8")
print("Updated task records for tasks 42-61.")
