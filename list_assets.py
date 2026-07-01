import json
import os

root = os.path.abspath('.')
js_files = []
html_files = []
for dirpath, _, filenames in os.walk(root):
    for f in filenames:
        if f.lower().endswith('.js'):
            js_files.append(os.path.relpath(os.path.join(dirpath, f), root))
        if f.lower().endswith('.html'):
            html_files.append(os.path.relpath(os.path.join(dirpath, f), root))
print('JS files:', json.dumps(js_files, indent=2))
print('HTML files:', json.dumps(html_files, indent=2))
