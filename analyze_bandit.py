import json

with open('bandit_report.json', 'r') as f:
    data = json.load(f)

print('BANDIT SECURITY SCAN RESULTS')
print('='*60)
print(f'Total issues: {len(data["results"])}')
print(f'High severity: {len([r for r in data["results"] if r["issue_severity"] == "HIGH"])}')
print(f'Medium severity: {len([r for r in data["results"] if r["issue_severity"] == "MEDIUM"])}')
print(f'Low severity: {len([r for r in data["results"] if r["issue_severity"] == "LOW"])}')
print()

print('HIGH SEVERITY ISSUES:')
print('='*60)
high_issues = [r for r in data['results'] if r['issue_severity'] == 'HIGH']
for issue in high_issues:
    print(f"File: {issue['filename']}")
    print(f"Line: {issue['line_number']}")
    print(f"Issue: {issue['issue_text']}")
    print(f"Test ID: {issue['test_id']}")
    print(f"Confidence: {issue['issue_confidence']}")
    print('-'*60)

print()
print('MEDIUM SEVERITY ISSUES (Top 10):')
print('='*60)
medium_issues = [r for r in data['results'] if r['issue_severity'] == 'MEDIUM']
for issue in medium_issues[:10]:
    print(f"File: {issue['filename']}")
    print(f"Line: {issue['line_number']}")
    print(f"Issue: {issue['issue_text']}")
    print(f"Test ID: {issue['test_id']}")
    print('-'*60)
