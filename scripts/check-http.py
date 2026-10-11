#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Read-only HTTP checks against the exact Pages subpath (Python 3.9)."""
import argparse
import hashlib
import json
import re
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import unquote, urljoin, urlsplit
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[1]
PREFIX = '/greenwakame-playground/'

class Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.values = []
        self.references = []
    def handle_starttag(self, tag, attrs):
        for key, value in attrs:
            if key in ('href', 'src') and value:
                self.values.append(value)
                self.references.append((tag, key, value, dict(attrs)))

def fetch(url):
    try:
        response = urlopen(url, timeout=20)
    except HTTPError as error:
        response = error
    with response:
        return response.code, response.headers, response.read(), response.geturl()

def mime_for(name):
    if Path(name).name.startswith('LICENSE') or name.endswith(('.md', '.txt')):
        return 'text/plain'
    suffix = Path(name).suffix
    return {'.html': 'text/html', '.css': 'text/css', '.js': 'text/javascript',
            '.json': 'application/json', '.wasm': 'application/wasm', '.png': 'image/png'}.get(suffix, 'text/plain')

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--origin', default='http://127.0.0.1:4183')
    parser.add_argument('--report', default='audit/http-check.json')
    parser.add_argument('--inventory', default='audit/public-inventory.json')
    args = parser.parse_args()
    report_path = ROOT / args.report
    assert not report_path.exists(), 'Refusing to overwrite an existing audit'
    origin = args.origin.rstrip('/')
    assert urlsplit(origin).hostname == '127.0.0.1', 'Loopback only'
    base = origin + PREFIX
    inventory = json.loads((ROOT / args.inventory).read_text(encoding='utf-8'))
    records = []
    internal = set()
    external = set()
    reference_count = 0
    permitted_data_icons = []
    for name, expected in inventory['manifest'].items():
        url = base + name
        status, headers, body, final = fetch(url)
        assert status == 200, (url, status)
        assert final == url, (url, final)
        assert headers.get_content_type() == mime_for(name), (name, headers.get('Content-Type'))
        assert int(headers['Content-Length']) == len(body) == expected['bytes'], name
        assert hashlib.sha256(body).hexdigest() == expected['sha256'], name
        assert body == (ROOT / 'site' / name).read_bytes(), name
        assert headers.get('X-Content-Type-Options') == 'nosniff', name
        records.append({'path': name, 'status': status, 'contentType': headers['Content-Type'],
                        'bytes': len(body), 'sha256': expected['sha256'], 'contentMatches': True})
        if name.endswith('.html'):
            text = body.decode('utf-8')
            assert not re.search(r'''["']/((?:assets|src|@vite|node_modules)/)''', text), name
            links = Links()
            links.feed(text)
            for tag, key, value, attributes in links.references:
                raw = urlsplit(value)
                if raw.scheme == 'data':
                    assert (tag == 'link' and key == 'href' and
                            'icon' in attributes.get('rel', '').lower().split() and
                            value == 'data:,'), ('Unapproved data URL', name, tag, key, value)
                    permitted_data_icons.append({'page': name, 'value': value, 'purpose': 'empty favicon'})
                    continue
                assert raw.scheme in ('', 'http', 'https'), (
                    'Forbidden URL scheme; mailto, javascript and unknown schemes are not allowed',
                    name, value)
                resolved = urlsplit(urljoin(url, value))
                if resolved.netloc == urlsplit(origin).netloc:
                    reference_count += 1
                    assert resolved.path.startswith(PREFIX), (name, value)
                    internal.add(resolved.path)
                else:
                    assert resolved.scheme == 'https', (name, value)
                    external.add(value)
    link_records = []
    for path in sorted(internal):
        status, headers, body, final = fetch(origin + path)
        assert status == 200, (path, status)
        relative = unquote(path[len(PREFIX):])
        local = ROOT / 'site' / relative
        if local.is_dir():
            local = local / 'index.html'
        assert local.is_file() and body == local.read_bytes(), path
        link_records.append({'path': path, 'status': status, 'contentMatches': True})
    negatives = []
    missing = [PREFIX + 'missing/', PREFIX + 'assets/absent.js',
               PREFIX + 'works/midnight-inspection/v0.1.0-phase1/assets/absent.wasm',
               '/assets/site.css', '/work/phase1-source.tar',
               PREFIX + 'work/phase1-source.tar', PREFIX + '%2e%2e/work/phase1-source.tar']
    fallback = (ROOT / 'site/404.html').read_bytes()
    for path in missing:
        status, headers, body, final = fetch(origin + path)
        assert status == 404, ('Missing resource must not return 200', path, status)
        assert headers.get_content_type() == 'text/html', path
        assert body == fallback, path
        negatives.append({'path': path, 'status': status, 'fallbackBodyMatches': True})
    status, headers, body, final = fetch(origin + '/')
    assert status == 200 and final == base
    assert body == (ROOT / 'site/index.html').read_bytes()
    version = ROOT / 'site/works/midnight-inspection/v0.1.0-phase1'
    info = json.loads((version / 'build-info.json').read_text(encoding='utf-8'))
    expected_base = PREFIX + 'works/midnight-inspection/v0.1.0-phase1/'
    assert expected_base in json.dumps(info), 'Build metadata base mismatch'
    game_html = (version / 'index.html').read_text(encoding='utf-8')
    game_links = Links()
    game_links.feed(game_html)
    assets = [value for value in game_links.values if value.endswith(('.js', '.css'))]
    assert assets and all(value.startswith(expected_base + 'assets/') for value in assets)
    assert reference_count == inventory['internalReferencesChecked']
    report = {'status': 'PASS', 'checkedAt': datetime.now(timezone.utc).isoformat(),
              'base': base, 'filesVerified': len(records), 'files': records,
              'internalReferencesChecked': reference_count, 'internalTargets': link_records,
              'externalLinks': sorted(external), 'negativeResponses': negatives,
              'permittedDataIcons': permitted_data_icons,
              'urlPolicy': {'data': 'Only exact data:, in link[rel~=icon][href]',
                            'mailto': 'Rejected; no approved contact links',
                            'javascript': 'Rejected', 'unknownSchemes': 'Rejected'},
              'rootRedirectVerified': True, 'viteBase': expected_base,
              'missingAssetsReturn404': True, 'fallbackReturns200': False,
              'notes': ['Explicit /404.html is an existing document and returns 200.',
                        'Missing documents/assets return HTTP 404 with the 404 HTML body.',
                        'LICENSE_AUDIT.json is served as text/plain by the existing server.',
                        'External links are inventoried, not certified for browser behavior.',
                        'Design user approved; P1-I-R1 assessed reviewed redistribution conditions as RELEASE READY, with incomplete Cargo.lock and some resolved versions unconfirmed. Prior user gameplay QA 8/8 PASS; its Chrome version is unrecorded. Publication requires separate approval.']}
    report_path.parent.mkdir(parents=True, exist_ok=True)
    with report_path.open('x', encoding='utf-8') as output:
        json.dump(report, output, ensure_ascii=False, indent=2)
        output.write('\n')
    print('HTTP PASS:', len(records), 'files;', reference_count, 'internal references;', len(missing), 'expected 404 responses')
    print('Correct Vite base; matching SHA256/content; MIME checks; no soft-404 assets')
    print('Report:', report_path)

if __name__ == '__main__':
    main()
