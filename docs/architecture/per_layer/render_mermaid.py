"""Render per-layer Mermaid .mmd files to .svg using mermaid.ink."""

import base64
import json
import sys
import zlib
from pathlib import Path

import requests


def encode_mermaid(text: str) -> str:
    """Encode Mermaid source for mermaid.ink URL.

    mermaid.ink uses the same format as the Mermaid Live Editor:
    a JSON state object (code + theme) compressed with zlib and base64url encoded,
    prefixed with 'pako:'.
    """
    state = {"code": text, "mermaid": {"theme": "default"}}
    state_json = json.dumps(state, ensure_ascii=False, separators=(",", ":"))
    compressed = zlib.compress(state_json.encode("utf-8"), 9)
    encoded = base64.urlsafe_b64encode(compressed).decode("ascii")
    return f"pako:{encoded}"


def render_file(mmd_path: Path) -> Path:
    source = mmd_path.read_text(encoding="utf-8")
    encoded = encode_mermaid(source)
    url = f"https://mermaid.ink/svg/{encoded}"
    response = requests.get(url, timeout=60)
    response.raise_for_status()
    out_path = mmd_path.with_suffix(".svg")
    out_path.write_bytes(response.content)
    print(f"Rendered {mmd_path} -> {out_path}")
    return out_path


def main() -> None:
    root = Path(__file__).parent
    if len(sys.argv) > 1:
        files = [Path(p) for p in sys.argv[1:]]
    else:
        files = sorted(root.glob("layer_*.mmd"))

    for mmd_file in files:
        if not mmd_file.exists():
            print(f"File not found: {mmd_file}")
            continue
        try:
            render_file(mmd_file)
        except Exception as exc:  # noqa: BLE001
            print(f"Failed to render {mmd_file}: {exc}")


if __name__ == "__main__":
    main()
