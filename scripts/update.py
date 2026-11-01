import json, os, urllib.request, datetime
from pathlib import Path
API='https://api.github.com/repos/LiveContainer/LiveContainer/releases/tags/nightly'
OUT=Path('apps.json')
def get(url):
    req=urllib.request.Request(url,headers={'User-Agent':'LC-Nightly-Source','Accept':'application/vnd.github+json','Authorization':'Bearer '+os.environ.get('GH_TOKEN','') } if os.environ.get('GH_TOKEN') else {'User-Agent':'LC-Nightly-Source','Accept':'application/vnd.github+json'})
    with urllib.request.urlopen(req,timeout=25) as r:return json.load(r)
release=get(API)
assets=release.get('assets',[])
asset=next((a for a in assets if a['name'].lower() in ('livecontainer+sidestore.ipa','livecontainer%2bsidestore.ipa')),None)
if not asset:
    print('No combined Nightly IPA; preserving existing source without stable fallback.')
    raise SystemExit(0)
# Extract real bundle version and identifier from an IPA when available, rather than inventing them.
import tempfile, zipfile, plistlib, urllib.request
with tempfile.NamedTemporaryFile(suffix='.ipa') as f:
    urllib.request.urlretrieve(asset['browser_download_url'],f.name)
    with zipfile.ZipFile(f.name) as z:
        plistname=next((n for n in z.namelist() if n.startswith('Payload/') and n.count('/')==2 and n.endswith('.app/Info.plist')),None)
        if not plistname:
            plistname=next(n for n in z.namelist() if n.startswith('Payload/') and n.endswith('.app/Info.plist'))
        info=plistlib.loads(z.read(plistname))
version=str(info['CFBundleShortVersionString'])
bundle=info['CFBundleIdentifier']
date=(release.get('published_at') or asset['created_at'])[:10]
source={'name':'LiveContainer + SideStore Nightly Only','identifier':'community.livecontainer.sidestore.nightlyonly','subtitle':'Official combined nightly IPA only','description':'Tracks only official combined LiveContainer+SideStore Nightly assets. No stable fallback.','apps':[{'name':'LiveContainer + SideStore Nightly','bundleIdentifier':bundle,'developerName':'LiveContainer contributors','subtitle':'Combined nightly build','localizedDescription':'Unofficial source index pointing to the official combined Nightly IPA.','iconURL':'https://raw.githubusercontent.com/LiveContainer/LiveContainer/main/LiveContainer/Assets.xcassets/AppIcon.appiconset/Icon-1024.png','versions':[{'version':version,'date':date,'downloadURL':asset['browser_download_url'],'size':asset['size'],'localizedDescription':release.get('name','Nightly')}]}]}
OUT.write_text(json.dumps(source,ensure_ascii=False,indent=2)+'\n')
print('Updated:',version,date)
