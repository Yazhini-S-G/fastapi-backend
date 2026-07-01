import json
import os

root = os.path.abspath('.')
html_files = []
for dirpath, _, filenames in os.walk(root):
    for f in filenames:
        if f.lower().endswith('.html'):
            html_files.append(os.path.join(dirpath, f))

results = []
for path in html_files:
    with open(path, encoding='utf-8') as fh:
        content = fh.read()
        if '<script' in content:
            results.append(path)
print(json.dumps(results, indent=2))
