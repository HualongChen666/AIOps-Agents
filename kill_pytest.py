# -*- coding: utf-8 -*-
import psutil


def should_kill(p: psutil.Process) -> bool:
    try:
        cmd = p.cmdline()
    except (psutil.AccessDenied, psutil.NoSuchProcess, OSError):
        return False
    if not cmd:
        return False
    text = " ".join(cmd)
    return "python" in p.name().lower() and any(
        token in text for token in ("pytest", "coverage", "run_coverage_phases", "run_core_api_infrastructure_tests", "run_cov_config")
    )


def main() -> None:
    for p in psutil.process_iter(["pid", "name"]):
        if should_kill(p):
            print(f"Killing {p.pid} {p.name()}")
            try:
                p.terminate()
                p.wait(timeout=3)
            except Exception:
                try:
                    p.kill()
                except Exception:
                    pass


if __name__ == "__main__":
    main()
