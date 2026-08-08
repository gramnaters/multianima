import re
import requests

UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'

def extract_vidmoly(embed_url: str) -> dict:
    try:
        resp = requests.get(embed_url, headers={'User-Agent': UA, 'Referer': embed_url}, timeout=15)
        html = resp.text

        m3u8_match = re.search(r"file:\s*'([^']*\.m3u8[^']*)'", html)
        if m3u8_match:
            return {'streams': [{'player': 'direct_m3u8', 'url': m3u8_match.group(1), 'name': 'VMoly', 'languages': []}]}

        sources = re.search(r'sources:\s*\[(.*?)\]', html, re.DOTALL)
        if sources:
            file_match = re.search(r'file:\s*["\']([^"\']+)["\']', sources.group(1))
            if file_match:
                return {'streams': [{'player': 'direct_m3u8', 'url': file_match.group(1), 'name': 'VMoly', 'languages': []}]}
    except Exception as e:
        print(f'[vidmoly] error: {e}')
    return {'streams': []}
