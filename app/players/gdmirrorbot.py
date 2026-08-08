import json
import base64
import requests

UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
API_URL = 'https://pro.iqsmartgames.com/embedhelper2.php'

def extract_gdmirrorbot(embed_url: str) -> dict:
    sid = embed_url.rstrip('/').split('/')[-1]
    referer = f'https://gdmirrorbot.nl/embed/{sid}'

    resp = requests.post(API_URL, headers={
        'User-Agent': UA,
        'Content-Type': 'application/x-www-form-urlencoded',
        'Origin': 'https://gdmirrorbot.nl',
        'Referer': referer,
    }, data={
        'sid': sid,
        'UserFavSite': '',
        'currentDomain': '[]',
    }, timeout=15)
    data = resp.json()

    if data.get('domain_blocked'):
        return {'streams': []}

    sources = data.get('sources', {})
    mresult = json.loads(base64.b64decode(data['mresult']))

    streams = []
    for key, config in sources.items():
        skey = mresult.get(key)
        if not skey: continue
        url = config['siteUrl'] + skey + (config.get('embed_suffix') or '')
        friendly = config.get('friendlyName', key)
        streams.append({
            'player': 'generic_embed',
            'url': url,
            'name': f'GDMirror/{friendly}',
            'languages': [],
        })
    return {'streams': streams}
