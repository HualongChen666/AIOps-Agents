#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Simple configuration validation script.
Checks that the three environment configuration YAML files exist,
contain required top‑level sections, and that any environment variable
placeholders (${VAR}) have a corresponding OS environment variable set.
"""

import os
import re
import sys

import yaml


def load_yaml(path):
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def check_placeholders(data, path):
    pattern = re.compile(r"\${([A-Z0-9_]+)}")
    missing = []

    def recurse(v):
        if isinstance(v, str):
            for m in pattern.findall(v):
                if os.getenv(m) is None:
                    missing.append(m)
        elif isinstance(v, dict):
            for val in v.values():
                recurse(val)
        elif isinstance(v, list):
            for item in v:
                recurse(item)

    recurse(data)
    if missing:
        print(f"❌ Missing env vars in {path}: {', '.join(set(missing))}")
        return False
    return True


def main():
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "config"))
    required_top = ["system", "postgres", "redis"]
    ok = True
    for fn in ["development.yaml", "staging.yaml", "production.yaml"]:
        p = os.path.join(base_dir, fn)
        if not os.path.isfile(p):
            print(f"❌ Config file missing: {p}")
            ok = False
            continue
        cfg = load_yaml(p)
        for sec in required_top:
            if sec not in cfg:
                print(f"❌ Section '{sec}' missing in {p}")
                ok = False
        if not check_placeholders(cfg, p):
            ok = False
    if ok:
        print("✅ All configuration files are valid.")
        sys.exit(0)
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()
