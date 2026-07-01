import json
import os

root = os.path.abspath('.')
js_files = []
for dirpath, _dirnames, filenames in os.walk(root):
    for f in filenames:
        if f.lower().endswith('.js'):
            rel = os.path.relpath(os.path.join(dirpath, f), root)
            js_files.append(rel)
print(json.dumps(js_files, indent=2))
