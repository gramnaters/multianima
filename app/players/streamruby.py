import re
import requests

UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'

def extract_streamruby(embed_url: str) -> dict:
    try:
        match = re.search(r'/e/(\w+)', embed_url)
        if not match: return {'streams': []}
        fid = match.group(1)

        resp = requests.post('https://streamruby.com/dl', headers={
            'User-Agent': UA, 'Content-Type': 'application/x-www-form-urlencoded',
            'Referer': embed_url, 'Origin': 'https://streamruby.com',
        }, data={'op': 'embed', 'file_code': fid, 'auto': '1', 'referer': ''}, timeout=15)
        html = resp.text

        # Unpack PACKER JS if present
        packed = re.match(r'.*eval\(function\(p,a,c,k,e,d\)', html)
        if packed:
            unpack_match = re.search(r"\}\('(.*?)',(\d+),(\d+),'([^']+)'\.split\('\|'\)", html)
            if unpack_match:
                packed_str, radix, count, keys_str = unpack_match.groups()
                keys = keys_str.split('|')
                base = int(radix)
                html = re.sub(r'\b\w+\b', lambda w: keys[int(w.group(), base)] if w.group().isalnum() and int(w.group(), base) < len(keys) else w.group(), packed_str)

        m3u8 = re.search(r'file:\s*"(https?://[^"]*\.m3u8[^"]*)"', html)
        if m3u8:
            return {'streams': [{'player': 'direct_m3u8', 'url': m3u8.group(1), 'name': 'StreamRuby', 'languages': []}]}

        sources = re.search(r'sources:\s*\[(.*?)\]', html, re.DOTALL)
        if sources:
            file_match = re.search(r'file:\s*"([^"]+)"', sources.group(1))
            if file_match:
                return {'streams': [{'player': 'direct_m3u8', 'url': file_match.group(1), 'name': 'StreamRuby', 'languages': []}]}
    except Exception as e:
        print(f'[streamruby] error: {e}')
    return {'streams': []}
