import os
import codecs
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
os.chdir(BASE_DIR)

with codecs.open('frontend/index.html', 'r', encoding='utf-8') as f:
    html = f.read()

with codecs.open('frontend/app.js', 'r', encoding='utf-8') as f:
    js = f.read()

placeholder = '<script type="text/babel" src="app.js?v=4"></script>'
if placeholder in html:
    html = html.replace(placeholder, '<script type="text/babel">\n' + js + '\n</script>')
else:
    start_tag = '<script type="text/babel">'
    start_idx = html.find(start_tag)
    end_idx = html.rfind('</script>')
    if start_idx != -1 and end_idx != -1:
        html = html[:start_idx + len(start_tag)] + "\n" + js + "\n" + html[end_idx:]
        print("Updated existing inlined JS inside index.html.")
    else:
        print("Error: Could not find script tag in index.html!")

with codecs.open('frontend/index.html', 'w', encoding='utf-8') as f:
    f.write(html)

print('Inlined successfully!')
