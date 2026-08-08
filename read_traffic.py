"""Read the mitmproxy 'all traffic' file and extract every flow's request/response details."""
import re
import json
import sys
import os
from datetime import datetime

FILE = os.path.join(os.path.dirname(__file__), "all traffic")

def extract_flows(data):
    """Parse mitmproxy flow format - each flow is separated by markers."""
    flows = []
    
    # Find flow boundaries using timestamps
    # Pattern: flow marker starts with content-length or type info
    # Let's find all URL patterns and their surrounding context
    
    # First, let's find all request/response pairs by looking for HTTP methods and URLs
    # The mitmproxy format stores: method, url, headers, body
    
    # Split by flow markers - look for common patterns
    # Each flow seems to start with metadata about request/response
    
    # Try to find all host:port patterns (these are in the CONNECT requests)
    host_pattern = rb'CONNECT ([^\s]+):\d+'
    hosts = set()
    for m in re.finditer(host_pattern, data):
        hosts.add(m.group(1).decode('utf-8', errors='ignore'))
    
    print(f"Found {len(hosts)} unique hosts from CONNECT requests:")
    for h in sorted(hosts):
        print(f"  {h}")
    print()
    
    # Find all URLs with full paths
    url_pattern = rb'(GET|POST|PUT|DELETE|HEAD|OPTIONS|PATCH) (https?://[^\s\x00-\x1f]+)'
    urls = []
    for m in re.finditer(url_pattern, data):
        method = m.group(1).decode()
        url = m.group(2).decode('utf-8', errors='ignore')
        urls.append((method, url))
    
    print(f"Found {len(urls)} request URLs:")
    for method, url in urls:
        print(f"  {method} {url[:200]}")
    print()

    # Also find relative URLs that follow a Host header
    # Pattern: "host: xxx\r\n..." followed by "GET /path"
    
    return urls, hosts

def find_video_streams(data):
    """Find m3u8, mp4, ts segments, and other video-related URLs."""
    patterns = [
        (rb'(https?://[^\s\x00-\x1f"\'<>]+\.m3u8[^\s\x00-\x1f"\'<>]*)', 'm3u8'),
        (rb'(https?://[^\s\x00-\x1f"\'<>]+\.ts[^\s\x00-\x1f"\'<>]*)', 'ts-segment'),
        (rb'(https?://[^\s\x00-\x1f"\'<>]+\.mp4[^\s\x00-\x1f"\'<>]*)', 'mp4'),
        (rb'(https?://[^\s\x00-\x1f"\'<>]+\.mpd[^\s\x00-\x1f"\'<>]*)', 'mpd'),
        (rb'(https?://[^\s\x00-\x1f"\'<>]+\.js[^\s\x00-\x1f"\'<>]*)', 'javascript'),
        (rb'(https?://[^\s\x00-\x1f"\'<>]+/manifest[^\s\x00-\x1f"\'<>]*)', 'manifest'),
        (rb'(https?://[^\s\x00-\x1f"\'<>]+/playlist[^\s\x00-\x1f"\'<>]*)', 'playlist'),
    ]
    
    results = {}
    for pattern, name in patterns:
        found = set()
        for m in re.finditer(pattern, data):
            url = m.group(1).decode('utf-8', errors='ignore').rstrip(',;)"\'')
            found.add(url)
        if found:
            results[name] = found
            print(f"\n=== {name.upper()} URLs ({len(found)} unique) ===")
            for url in sorted(found):
                print(f"  {url[:300]}")
    
    return results

def find_api_endpoints(data):
    """Find API-like endpoints."""
    patterns = [
        (rb'(https?://[^\s\x00-\x1f"\'<>]+/api/[^\s\x00-\x1f"\'<>]*)', 'API'),
        (rb'(https?://[^\s\x00-\x1f"\'<>]+/v\d/[^\s\x00-\x1f"\'<>]*)', 'Versioned API'),
        (rb'(https?://[^\s\x00-\x1f"\'<>]+/graphql[^\s\x00-\x1f"\'<>]*)', 'GraphQL'),
        (rb'(https?://[^\s\x00-\x1f"\'<>]+/embed[^\s\x00-\x1f"\'<>]*)', 'Embed'),
    ]
    
    for pattern, name in patterns:
        found = set()
        for m in re.finditer(pattern, data):
            url = m.group(1).decode('utf-8', errors='ignore').rstrip(',;)"\'')
            found.add(url)
        if found:
            print(f"\n=== {name} URLs ({len(found)} unique) ===")
            for url in sorted(found)[:50]:
                print(f"  {url[:300]}")

def find_player_refs(data):
    """Find references to known player domains."""
    known_players = [
        'zephyrflick', 'zephyrix', 'abyssplayer', 'bilibili', 'pahe',
        'gd', 'mirror', 'bot', 'gdmirrorbot', 'cloud', 'flix',
        'megacloud', 'megaplay', 'mewstream', 'streamtape', 'streamruby',
        'streamhg', 'hanerix', 'vidmoly', 'dood', 'p2pplay', 'rpmstream',
        'upns', 'blakite', 'iqsmart', 'zn-grid', 'cdn',
        'pahe', 'uwu', 'desi', 'anime', 'toon', 'hindi',
        'zephyr', 'as-cdn'
    ]
    
    text = data.decode('utf-8', errors='ignore').lower()
    print("\n=== PLAYER DOMAIN REFERENCES ===")
    for player in known_players:
        count = text.count(player.lower())
        if count > 0:
            print(f"  '{player}': {count} references")

def find_headers_and_cookies(data):
    """Find interesting headers, cookies, auth tokens."""
    # Look for Authorization headers
    auth_pattern = rb'Authorization[:\s]+([^\r\n]+)'
    for m in re.finditer(auth_pattern, data):
        print(f"Auth header: {m.group(1).decode('utf-8', errors='ignore')[:200]}")
    
    # Look for Set-Cookie
    cookie_pattern = rb'Set-Cookie[:\s]+([^\r\n]+)'
    cookies_found = set()
    for m in re.finditer(cookie_pattern, data):
        cookie = m.group(1).decode('utf-8', errors='ignore')[:200]
        cookies_found.add(cookie)
    if cookies_found:
        print(f"\n=== SET-COOKIE HEADERS ({len(cookies_found)} unique) ===")
        for c in sorted(cookies_found):
            print(f"  {c}")
    
    # Look for Bearer tokens
    bearer_pattern = rb'Bearer[ ]+([A-Za-z0-9._\-]+)'
    for m in re.finditer(bearer_pattern, data):
        print(f"Bearer token: {m.group(1).decode('utf-8', errors='ignore')[:100]}")

if __name__ == '__main__':
    print(f"Reading file: {FILE}")
    print(f"File size: {os.path.getsize(FILE) / 1024 / 1024:.1f} MB")
    print()
    
    with open(FILE, 'rb') as f:
        data = f.read()
    
    print("=" * 80)
    print("BASIC URL EXTRACTION")
    print("=" * 80)
    urls, hosts = extract_flows(data)
    
    print("=" * 80)
    print("VIDEO STREAM URLs")
    print("=" * 80)
    find_video_streams(data)
    
    print("\n" + "=" * 80)
    print("API ENDPOINTS")
    print("=" * 80)
    find_api_endpoints(data)
    
    print("\n" + "=" * 80)
    print("PLAYER REFERENCES")
    print("=" * 80)
    find_player_refs(data)
    
    print("\n" + "=" * 80)
    print("HEADERS & COOKIES")
    print("=" * 80)
    find_headers_and_cookies(data)
    
    print("\n" + "=" * 80)
    print("DONE")
    print("=" * 80)
