import json

with open('coverage_summary.json') as f:
    data = json.load(f)

print('top keys:', list(data.keys())[:5])
print('totals:', data.get('totals'))
files = data['files']
print('num files:', len(files))
for i, (k,v) in enumerate(list(files.items())[:3]):
    print(k, v.get('summary'))
