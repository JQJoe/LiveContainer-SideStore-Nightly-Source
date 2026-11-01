#!/usr/bin/env python3
"""Generate an AltStore/SideStore source from the official combined Nightly IPA.

Only accepts a real asset attached to LiveContainer's `nightly` GitHub release.
Never falls back to stable or constructs an unverified asset URL.
"""
import datetime as dt
import io
import json
import os
from pathlib import Path
import plistlib
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
import zipfile

OWNER = 'LiveContainer'
REPO = 'LiveContainer'
TAG = 'nightly'
SOURCE_URL = 'https://raw.githubusercontent.com/JQJoe/LiveContainer-SideStore-Nightly-Source/main/apps.json'
OUTPUT = Path(os.environ.get('SOURCE_OUTPUT', 'apps.json'))
API = f'https://api.github.com/repos/{OWNER}/{REPO}/releases/tags/{TAG}'
TOKEN = os.environ.get('GH_TOKEN', '')


def request(url, accept='application/vnd.github+json'):
    headers = {'User-Agent': 'lc-sidestore-nightly-source/2.0', 'Accept': accept}
    if TOKEN and urllib.parse.urlsplit(url).hostname == 'api.github.com':
        headers['Authorization'] = f'Bearer {TOKEN}'
    return urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=60)


def asset_is_combined(name):
    """Match only IPA assets explicitly named for both LiveContainer and SideStore."""
    if not name.lower().endswith('.ipa'):
        return False
    normalized = re.sub(r'[^a-z0-9]', '', urllib.parse.unquote(name).lower())
    return 'livecontainer' in normalized and 'sidestore' in normalized


def main():
    with request(API) as response:
        release = json.load(response)
    assets = release.get('assets') or []
    matches = [a for a in assets if asset_is_combined(a.get('name', ''))]
    if not matches:
        names = ', '.join(a.get('name', '?') for a in assets) or '(none)'
        raise RuntimeError(f'No official combined Nightly IPA found in {TAG!r}. Release assets: {names}. Existing apps.json untouched.')
    if len(matches) > 1:
        raise RuntimeError('Multiple combined Nightly IPAs found; refusing ambiguous selection: ' + ', '.join(a['name'] for a in matches))
    asset = matches[0]
    download_url = asset['browser_download_url']
    size = int(asset['size'])
    if size <= 0 or not download_url.startswith(f'https://github.com/{OWNER}/{REPO}/releases/download/'):
        raise RuntimeError('Release asset has invalid size or download URL')

    # Avoid downloading the same large IPA on every scheduled run.
    previous = {}
    if OUTPUT.exists():
        try:
            previous = json.loads(OUTPUT.read_text(encoding='utf-8'))
        except (ValueError, OSError):
            pass
    old = ((previous.get('apps') or [{}])[0].get('versions') or [{}])[0]
    asset_timestamp = asset.get('updated_at') or asset.get('created_at') or release['published_at']
    # Build metadata stored in the source lets us detect a replaced Nightly asset.
    old_marker = old.get('localizedDescription', '')
    marker = f"nightly-{asset['id']}-{asset_timestamp}"
    if marker in old_marker and old.get('downloadURL') == download_url:
        print('No change in official Nightly asset; apps.json unchanged.')
        return

    print(f"Downloading verified release asset: {asset['name']} ({size} bytes)")
    with request(download_url, accept='application/octet-stream') as response:
        ipa_bytes = response.read()
    if len(ipa_bytes) != size:
        raise RuntimeError(f'IPA size mismatch: expected {size}, got {len(ipa_bytes)}')
    with zipfile.ZipFile(io.BytesIO(ipa_bytes)) as ipa:
        info_paths = [p for p in ipa.namelist() if re.fullmatch(r'Payload/[^/]+\.app/Info\.plist', p)]
        if len(info_paths) != 1:
            raise RuntimeError(f'Expected one app Info.plist, got {info_paths}')
        info = plistlib.loads(ipa.read(info_paths[0]))

    bundle_id = str(info.get('CFBundleIdentifier') or '').strip()
    version = str(info.get('CFBundleShortVersionString') or '').strip()
    build = str(info.get('CFBundleVersion') or '').strip()
    if not bundle_id or not version or not build:
        raise RuntimeError('IPA is missing CFBundleIdentifier, CFBundleShortVersionString or CFBundleVersion')
    date = asset_timestamp[:10]
    app = {
        'name': 'LiveContainer + SideStore Nightly',
        'bundleIdentifier': bundle_id,
        'developerName': 'LiveContainer contributors',
        'subtitle': 'Official combined Nightly IPA',
        'localizedDescription': 'Community-maintained index of the official LiveContainer + SideStore Nightly release. No stable fallback.',
        'iconURL': 'https://github.com/LiveContainer.png',
        'version': version,
        'versionDate': date,
        'downloadURL': download_url,
        'size': size,
        'versions': [{
            'version': version,
            'date': date,
            'downloadURL': download_url,
            'size': size,
            'localizedDescription': f'Official combined Nightly • build {build} • {date} • {marker}',
        }],
    }
    source = {
        'name': 'LiveContainer + SideStore Nightly Only',
        'identifier': 'community.livecontainer.sidestore.nightlyonly',
        'sourceURL': SOURCE_URL,
        'subtitle': 'Official combined nightly IPA only',
        'description': 'Tracks only official combined LiveContainer+SideStore Nightly assets. No stable fallback.',
        'iconURL': 'https://github.com/LiveContainer.png',
        'apps': [app],
    }
    rendered = json.dumps(source, indent=2, ensure_ascii=False) + '\n'
    OUTPUT.write_text(rendered, encoding='utf-8')
    print(f"Wrote {OUTPUT}: {bundle_id} {version} ({build}), asset {asset['name']}")


if __name__ == '__main__':
    try:
        main()
    except (urllib.error.URLError, OSError, ValueError, KeyError, RuntimeError, zipfile.BadZipFile) as error:
        print(f'ERROR: {error}', file=sys.stderr)
        sys.exit(1)
