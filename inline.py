import os
import codecs
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
os.chdir(BASE_DIR)

with codecs.open('frontend/index.html', 'r', encoding='utf-8') as f:
    html = f.read()

with codecs.open('frontend/app.js', 'r', encoding='utf-8') as f:
    js = f.read()

html = html.replace('<script type="text/babel" src="app.js?v=4"></script>', '<script type="text/babel">\n' + js + '\n</script>')

with codecs.open('frontend/index.html', 'w', encoding='utf-8') as f:
    f.write(html)

print('Inlined successfully!')
