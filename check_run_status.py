import json
import subprocess
from datetime import datetime
from pathlib import Path

ps = subprocess.run(
    [
        "powershell",
        "-NoProfile",
        "-Command",
        "Get-Process python -ErrorAction SilentlyContinue | "
        "Select-Object Id, Path, StartTime | Format-Table -AutoSize",
    ],
    capture_output=True,
    text=True,
    errors="ignore",
)
logs = []
for p in Path("coverage_logs").glob("phase_*.log"):
    logs.append({"name": p.name, "size": p.stat().st_size, "mtime": p.stat().st_mtime})

Path("run_status.txt").write_text(
    f"Checked at {datetime.now().isoformat()}\n"
    f"PS output:\n{ps.stdout}\n"
    f"PS stderr:\n{ps.stderr}\n"
    f"Log files:\n{json.dumps(logs, indent=2)}\n",
    encoding="utf-8"
)
