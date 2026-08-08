import re
import requests

UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'

def extract_doodstream(embed_url: str) -> dict:
    try:
        resp = requests.get(embed_url, headers={'User-Agent': UA}, timeout=15)
        html = resp.text

        # Direct download URL
        dl_match = re.search(r"\$\.get\('(/download/[^']+)'", html)
        if dl_match:
            base = '/'.join(embed_url.split('/')[:3])
            dl_resp = requests.get(base + dl_match.group(1), headers={'Referer': embed_url}, timeout=15)
            if '.mp4' in dl_resp.url or 'video' in dl_resp.headers.get('content-type', ''):
                return {'streams': [{'player': 'direct_m3u8', 'url': dl_resp.url, 'name': 'DoodStream', 'languages': []}]}

        # Pass MD5 pattern
        pass_match = re.search(r"pass_md5[=:]\s*['\"]([^'\"]+)", html)
        if pass_match:
            base = '/'.join(embed_url.split('/')[:3])
            pass_resp = requests.get(f'{base}/pass_md5/{pass_match.group(1)}', headers={'Referer': embed_url}, timeout=15)
            final = re.search(r'(https?://[^\s\'\"<>]+\.(?:mp4|m3u8)[^\s\'\"<>]*)', pass_resp.text)
            if final:
                return {'streams': [{'player': 'direct_m3u8', 'url': final.group(1), 'name': 'DoodStream', 'languages': []}]}

        # File source
        file_match = re.search(r'file:\s*"([^"]+)"', html)
        if file_match:
            return {'streams': [{'player': 'direct_m3u8', 'url': file_match.group(1), 'name': 'DoodStream', 'languages': []}]}
    except Exception as e:
        print(f'[doodstream] error: {e}')
    return {'streams': []}
