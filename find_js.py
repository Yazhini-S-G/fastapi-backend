import json
import os

root = os.path.abspath('.')
js_files = []
for dirpath, _, filenames in os.walk(root):
    for f in filenames:
        if f.lower().endswith('.js'):
            js_files.append(os.path.relpath(os.path.join(dirpath, f), root))
print(json.dumps(js_files, indent=2))
