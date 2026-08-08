import re
import base64
import requests

UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'

def extract_streamp2p(embed_url: str) -> dict:
    try:
        resp = requests.get(embed_url, headers={'User-Agent': UA, 'Referer': embed_url}, timeout=15)
        html = resp.text

        # Direct file match
        file_match = re.search(r"(?:file|src):\s*['\"]([^'\"]*(?:m3u8|mp4)[^'\"]*)['\"]", html)
        if file_match:
            return {'streams': [{'player': 'direct_m3u8', 'url': file_match.group(1), 'name': 'StreamP2P', 'languages': []}]}

        # Base64
        b64_match = re.search(r'atob\("([^"]+)"\)', html)
        if b64_match:
            try:
                decoded = base64.b64decode(b64_match.group(1)).decode()
                return {'streams': [{'player': 'direct_m3u8', 'url': decoded, 'name': 'StreamP2P', 'languages': []}]}
            except: pass

        # Packed JS
        packed = re.search(r"eval\(function\(p,a,c,k,e,d\)", html)
        if packed:
            unpack_match = re.search(r"\}\('(.*?)',(\d+),(\d+),'([^']+)'\.split\('\|'\)", html)
            if unpack_match:
                packed_str, radix, count, keys_str = unpack_match.groups()
                keys = keys_str.split('|')
                base = int(radix)
                unpacked = re.sub(r'\b\w+\b', lambda w: keys[int(w.group(), base)] if w.group().isalnum() and int(w.group(), base) < len(keys) else w.group(), packed_str)
                m3u8 = re.search(r'file:\s*"([^"]*(?:m3u8|mp4)[^"]*)"', unpacked)
                if m3u8:
                    return {'streams': [{'player': 'direct_m3u8', 'url': m3u8.group(1), 'name': 'StreamP2P', 'languages': []}]}
    except Exception as e:
        print(f'[streamp2p] error: {e}')
    return {'streams': []}


def extract_turbovid(embed_url: str) -> dict:
    """TurboVid extractor"""
    try:
        resp = requests.get(embed_url, headers={'User-Agent': UA}, timeout=15)
        html = resp.text

        sources = re.search(r'sources:\s*\[(.*?)\]', html, re.DOTALL)
        if sources:
            file_match = re.search(r'file:\s*["\']([^"\']+)["\']', sources.group(1))
            if file_match:
                return {'streams': [{'player': 'direct_m3u8', 'url': file_match.group(1), 'name': 'TurboVid', 'languages': []}]}

        # Base64 atob
        b64_match = re.search(r"atob\(['\"]([^'\"]+)['\"]\s*\)", html)
        if b64_match:
            try:
                decoded = base64.b64decode(b64_match.group(1)).decode()
                return {'streams': [{'player': 'direct_m3u8', 'url': decoded, 'name': 'TurboVid', 'languages': []}]}
            except: pass

        # API source
        id_match = re.search(r'embed-([a-zA-Z0-9]+)', embed_url)
        if id_match:
            base_url = '/'.join(embed_url.split('/')[:3])
            api_resp = requests.post(f'{base_url}/api/source/{id_match.group(1)}', headers={
                'User-Agent': UA, 'Referer': embed_url,
            }, json={}, timeout=15)
            try:
                data = api_resp.json()
                for item in (data.get('data') or [data]):
                    if item.get('file'):
                        return {'streams': [{'player': 'direct_m3u8', 'url': item['file'], 'name': 'TurboVid', 'languages': []}]}
            except: pass
    except Exception as e:
        print(f'[turbovid] error: {e}')
    return {'streams': []}
