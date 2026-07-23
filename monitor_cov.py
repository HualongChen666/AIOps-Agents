# -*- coding: utf-8 -*-
"""Monitor the background coverage process and write status/tail to files."""
import csv
import json
import time
from pathlib import Path

import psutil


def get_pid() -> int | None:
    csv_path = Path("cov_proc_config.csv")
    if not csv_path.exists():
        return None
    try:
        with csv_path.open(encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for row in reader:
                return int(row["Id"])
    except Exception:
        return None
    return None


def tail_log(log_path: Path, out_path: Path, n: int = 10) -> None:
    if not log_path.exists():
        out_path.write_text("log not found", encoding="utf-8")
        return
    try:
        text = log_path.read_text(encoding="utf-8", errors="replace")
        lines = text.splitlines()
        out_path.write_text("\n".join(lines[-n:]), encoding="utf-8")
    except Exception as exc:
        out_path.write_text(f"tail error: {exc}", encoding="utf-8")


def main() -> None:
    log_path = Path("cov_with_config.log")
    tail_path = Path("cov_tail.txt")
    status_path = Path("cov_status.json")
    pid = get_pid()
    if pid is None:
        status_path.write_text(json.dumps({"status": "NO_PID", "pid": None}), encoding="utf-8")
        return
    try:
        proc = psutil.Process(pid)
    except psutil.NoSuchProcess:
        status_path.write_text(
            json.dumps(
                {
                    "checked_at": time.strftime("%Y-%m-%d %H:%M:%S"),
                    "status": "DONE",
                    "pid": str(pid),
                }
            ),
            encoding="utf-8",
        )
        tail_log(log_path, tail_path)
        return

    while proc.is_running():
        status_path.write_text(
            json.dumps(
                {
                    "checked_at": time.strftime("%Y-%m-%d %H:%M:%S"),
                    "status": "RUNNING",
                    "pid": str(pid),
                }
            ),
            encoding="utf-8",
        )
        tail_log(log_path, tail_path)
        time.sleep(30)
        try:
            proc = psutil.Process(pid)
        except psutil.NoSuchProcess:
            break

    status_path.write_text(
        json.dumps(
            {
                "checked_at": time.strftime("%Y-%m-%d %H:%M:%S"),
                "status": "DONE",
                "pid": str(pid),
            }
        ),
        encoding="utf-8",
    )
    tail_log(log_path, tail_path)


if __name__ == "__main__":
    main()
