# -*- coding: utf-8 -*-

import yaml

OPENAPI_PATH = r"C:\\AIOps_Agent_bak\\openapi.yaml"


def load():
    with open(OPENAPI_PATH, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def main():
    spec = load()
    total = sum(len(m) for m in spec.get("paths", {}).values())
    missing_desc = []
    missing_params_desc = []
    missing_notes = []
    for path, methods in spec.get("paths", {}).items():
        for method, details in methods.items():
            if "description" not in details:
                missing_desc.append((path, method))
            for param in details.get("parameters", []):
                if "description" not in param:
                    missing_params_desc.append((path, method, param.get("name")))
            if "x-notes" not in details:
                missing_notes.append((path, method))
    print("Total endpoint definitions:", total)
    print("Missing description count:", len(missing_desc))
    print("Missing param description count:", len(missing_params_desc))
    print("Missing notes count:", len(missing_notes))
    # Optionally dump some examples
    if missing_desc:
        print("Example missing description:", missing_desc[:5])
    if missing_params_desc:
        print("Example missing param description:", missing_params_desc[:5])
    if missing_notes:
        print("Example missing notes:", missing_notes[:5])


if __name__ == "__main__":
    main()
