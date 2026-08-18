import glob
import re

for f in glob.glob('test_*.py'):
    with open(f, 'r', encoding='utf-8') as file:
        content = file.read()
    # Fix all imports to use the correct path
    content = re.sub(r'from knowledge_graph_service\.', 'from extensions.addons.ai_plus.knowledge_graph_service.', content)
    # Remove any sys.path modifications that were added
    lines = content.split('\n')
    new_lines = []
    skip_next = False
    for line in lines:
        if 'import sys' in line and 'import os' in line and 'from pathlib import Path' in line:
            skip_next = True
            continue
        if skip_next and ('Add parent directory' in line or 'parent_dir' in line or 'sys.path.insert' in line):
            continue
        if skip_next and line.strip() == '':
            skip_next = False
            continue
        new_lines.append(line)
    content = '\n'.join(new_lines)
    with open(f, 'w', encoding='utf-8') as file:
        file.write(content)
    print(f'Fixed {f}')
