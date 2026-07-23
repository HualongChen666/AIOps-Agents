#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Summarize final phase-4 verification JSON."""

import json
import sys
from pathlib import Path


def main() -> int:
    p = Path("C:/AIOps_Agent_bak/verify_logs/tasks_62_69_final_verification.json")
    data = json.loads(p.read_text(encoding="utf-8"))
    print(f"{'task':>4} {'service':30} black isort flake8 mypy bandit pytest coverage")
    all_ok = True
    for e in data:
        ok = (
            e["black"]["rc"] == 0
            and e["isort"]["rc"] == 0
            and e["flake8"]["rc"] == 0
            and e["mypy"]["rc"] == 0
            and e["bandit"]["rc"] == 0
            and e["pytest"]["rc"] == 0
        )
        if not ok:
            all_ok = False
        print(
            f"{e['task']:>4} {e['service'][:30]:30} "
            f"{e['black']['rc']:>5} {e['isort']['rc']:>5} {e['flake8']['rc']:>6} "
            f"{e['mypy']['rc']:>4} {e['bandit']['rc']:>6} {e['pytest']['rc']:>6} "
            f"{e.get('coverage_total', '?'):>8}"
        )
    print("\nall_ok:", all_ok)
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
