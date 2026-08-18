import glob
import re

for f in glob.glob('test_*.py'):
    with open(f, 'r') as file:
        content = file.read()
    content = re.sub(r'from knowledge_graph_service([a-z_])', r'from knowledge_graph_service.\1', content)
    with open(f, 'w') as file:
        file.write(content)
    print(f'Fixed {f}')
