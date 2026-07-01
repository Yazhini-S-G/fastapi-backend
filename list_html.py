import json
import os

root = os.getcwd()
html_files = []
for dirpath, _, filenames in os.walk(root):
    for f in filenames:
        if f.lower().endswith('.html'):
            html_files.append(os.path.relpath(os.path.join(dirpath, f), root))
print(json.dumps(html_files, indent=2))
