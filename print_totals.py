import json
from pathlib import Path
data = json.loads(Path("coverage.json").read_text(encoding="utf-8"))
print(json.dumps(data.get("totals"), indent=2, ensure_ascii=False))
