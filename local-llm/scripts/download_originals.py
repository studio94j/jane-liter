#!/usr/bin/env python3
"""Download unmodified Project Gutenberg UTF-8 editions and record provenance."""
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[2]
DEST = ROOT / 'data' / 'originals'
WORKS = [
    ('austen', 1342, 'pride-and-prejudice', 'Pride and Prejudice'),
    ('austen', 161, 'sense-and-sensibility', 'Sense and Sensibility'),
    ('austen', 158, 'emma', 'Emma'),
    ('austen', 141, 'mansfield-park', 'Mansfield Park'),
    ('austen', 105, 'persuasion', 'Persuasion'),
    ('austen', 121, 'northanger-abbey', 'Northanger Abbey'),
    ('austen', 946, 'lady-susan', 'Lady Susan'),
    ('shakespeare', 100, 'complete-works', 'The Complete Works of William Shakespeare'),
    ('chekhov', 1754, 'the-sea-gull', 'The Sea-Gull'),
    ('chekhov', 1756, 'uncle-vanya', 'Uncle Vanya'),
    ('chekhov', 7986, 'plays-second-series', 'Plays by Anton Chekhov, Second Series'),
    ('chekhov', 13415, 'lady-with-the-dog-and-other-stories', 'The Lady with the Dog and Other Stories'),
    ('chekhov', 13416, 'darling-and-other-stories', 'The Darling and Other Stories'),
]

def main():
    manifest = []
    previous = {e["path"]:e for e in json.loads((DEST/"manifest.json").read_text())} if (DEST/"manifest.json").exists() else {}
    for author, pgid, slug, title in WORKS:
        url = f'https://www.gutenberg.org/cache/epub/{pgid}/pg{pgid}.txt'
        target = DEST / author / f'{slug}.txt'
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists():
            data = target.read_bytes()
            retrieved_at = previous.get(str(target.relative_to(ROOT)),{}).get('retrieved_at',datetime.fromtimestamp(target.stat().st_mtime, timezone.utc).isoformat())
        else:
            data = subprocess.run(['/usr/bin/curl', '--fail', '--silent', '--show-error', '--location', '--retry', '2', '--max-time', '120', url], check=True, capture_output=True).stdout
            content = data.decode('utf-8-sig')
            if len(data) < 10000 or '*** START OF' not in content or '*** END OF' not in content or 'PROJECT GUTENBERG' not in content.upper():
                raise ValueError(f'Invalid/incomplete ebook response: {title}')
            target.write_bytes(data)
            retrieved_at = datetime.now(timezone.utc).isoformat()
        content = data.decode('utf-8-sig')
        manifest.append(dict(author=author, title=title, language='en', gutenberg_id=pgid,
                             source_page=f'https://www.gutenberg.org/ebooks/{pgid}', download_url=url,
                             path=str(target.relative_to(ROOT)), bytes=len(data), lines=len(content.splitlines()),
                             sha256=hashlib.sha256(data).hexdigest(), retrieved_at=retrieved_at,
                             preservation='Unmodified downloaded bytes, including Gutenberg header and license.'))
        if author == 'chekhov':
            edition=json.loads((DEST/'chekhov/catalog.json').read_text())[str(pgid)]
            manifest[-1].update(original_language='ru', text_kind='translation-en', translator=edition['translator'],
                                copyright_status='Public domain in the USA (Project Gutenberg catalog)',
                                copyright_source=f'https://www.gutenberg.org/ebooks/{pgid}')
        print(f'{author}/{slug}.txt: {len(data):,} bytes', flush=True)
    (DEST / 'manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')

if __name__ == '__main__':
    main()
