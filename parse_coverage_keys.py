import json

with open("coverage.json") as f:
    data = json.load(f)
for fn in data["files"]:
    if "database" in fn.lower():
        print(repr(fn))
