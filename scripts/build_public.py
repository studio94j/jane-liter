"""Publish only UI assets; corpus, prompts, keys and QA data stay private."""
from pathlib import Path
import shutil
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from ai.retrieval import ensure_index, stats

def build():
    ensure_index()
    shutil.copy2(ROOT / 'proto/situations.json', ROOT / 'cloud/situations.json')
    target = ROOT / 'public'
    if target.exists():
        shutil.rmtree(target)
    target.mkdir()
    files = ['index.html', 'styles.css', 'fonts.css', 'content.js', 'memory.js',
             'chat-archive.js', 'local-chat.js', 'prophecy-archive.js', 'fortune.js',
             'situations.js', 'situations.json', 'conversation-records.js', 'icons.js',
             'app.js', 'cloud-session.js', 'onboarding.js', 'onboarding.css']
    for name in files:
        shutil.copy2(ROOT / 'proto' / name, target / name)
    shutil.copytree(ROOT / 'proto/screens', target / 'screens')
    shutil.copytree(ROOT / 'proto/assets', target / 'assets',
                    ignore=shutil.ignore_patterns('.*', '*.md', '*.json', '*.fig'))
    print('Public UI built; full-text corpus:', stats())

if __name__ == '__main__':
    build()
