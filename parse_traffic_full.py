"""
Robust parser for mitmproxy flow dump file.
Reads the entire 772MB file and extracts every HTTP flow with full details.
"""
import re
import os
import sys
import json
import gzip
import zlib
import io
from collections import defaultdict, Counter
from datetime import datetime

FILE = os.path.join(os.path.dirname(__file__), "all traffic")
OUT_DIR = os.path.join(os.path.dirname(__file__), "traffic_analysis_full")
os.makedirs(OUT_DIR, exist_ok=True)

def decompress(data):
    try:
        return gzip.decompress(data)
    except:
        try:
            return zlib.decompress(data, 16 + zlib.MAX_WBITS)
        except:
            try:
                return zlib.decompress(data)
            except:
                return data

def parse_flow_file(data):
    """
    The file uses mitmproxy's flow serialization format.
    Each flow is a serialized object with request/response.
    Let's use a regex approach to find all HTTP exchanges.
    """
    flows = []
    
    # Find all HTTP requests and responses
    # Pattern: method URL HTTP/version \r\n headers \r\n body
    # Also look for the mitmproxy flow markers
    
    # Strategy: scan through file looking for HTTP method markers followed by URLs
    # and their response status codes
    
    # Let's find blocks between flow boundaries
    # In mitmproxy format, flows start with metadata
    
    # First pass: find all domain names and organize
    text = data.decode('utf-8', errors='ignore')
    
    # Find all unique hosts by looking for Host: headers
    host_pattern = re.compile(rb'Host:\s*([^\r\n]+)', re.IGNORECASE)
    hosts = Counter()
    for m in host_pattern.finditer(data):
        host = m.group(1).decode('utf-8', errors='ignore').strip()
        hosts[host] += 1
    
    print(f"Found {len(hosts)} unique Host headers, {sum(hosts.values())} total:")
    for host, count in hosts.most_common(100):
        print(f"  {host}: {count}")
    print()
    
    return hosts

def find_all_urls_complete(data):
    """Find every URL in the file with full context."""
    # Find URLs that appear in request lines: GET /path HTTP/1.1
    # Also find full URLs in Address, :authority, etc.
    
    all_requests = []
    
    # Pattern for request lines
    req_pattern = re.compile(rb'(GET|POST|PUT|DELETE|HEAD|OPTIONS|PATCH|CONNECT) ([^\s]+) HTTP/[\d.]+')
    for m in req_pattern.finditer(data):
        method = m.group(1).decode()
        url = m.group(2).decode('utf-8', errors='ignore')
        pos = m.start()
        # Get surrounding context (look backwards for the start of this flow)
        context_start = max(0, pos - 500)
        context = data[context_start:pos]
        # Find Host header in context
        host_match = re.search(rb'Host:\s*([^\r\n]+)', context)
        host = host_match.group(1).decode('utf-8', errors='ignore').strip() if host_match else ""
        all_requests.append((method, host, url, pos))
    
    print(f"Found {len(all_requests)} HTTP request lines")
    return all_requests

def find_response_codes(data):
    """Find all HTTP response status lines."""
    responses = []
    resp_pattern = re.compile(rb'HTTP/[\d.]+\s+(\d{3})\s*([^\r\n]*)')
    for m in resp_pattern.finditer(data):
        status = m.group(1).decode()
        reason = m.group(2).decode('utf-8', errors='ignore')
        responses.append((status, reason, m.start()))
    
    print(f"Found {len(responses)} HTTP response lines")
    return responses

def find_json_bodies(data):
    """Find JSON response/request bodies that might contain streaming URLs."""
    json_pattern = re.compile(rb'\{[^{}]{50,}?\}', re.DOTALL)
    found = []
    count = 0
    for m in json_pattern.finditer(data):
        try:
            text = m.group().decode('utf-8', errors='ignore')
            if any(kw in text.lower() for kw in ['m3u8', 'stream', 'video', 'source', 'file', 'url', 'link', 'embed', 'episode', 'server', 'quality', 'hls', 'mp4', 'iframe', 'media']):
                found.append(text[:2000])
                count += 1
                if count >= 500:
                    break
        except:
            pass
    
    print(f"Found {len(found)} relevant JSON bodies")
    return found

def find_embed_iframes(data):
    """Find iframe/embed URLs."""
    iframe_pattern = re.compile(rb'(?:src|url|link|embed|file)\s*[=:]\s*["\']?(https?://[^\s"\'<>]+)', re.IGNORECASE)
    found = set()
    for m in iframe_pattern.finditer(data):
        url = m.group(1).decode('utf-8', errors='ignore')
        if len(url) > 20:
            found.add(url)
    
    print(f"Found {len(found)} embed/iframe URLs")
    return found

def find_cookie_auth(data):
    """Find cookies and auth tokens."""
    results = {}
    
    # Cookies
    cookie_pattern = re.compile(rb'(Cookie|Set-Cookie|Authorization|X-Forwarded|Referer|Origin):\s*([^\r\n]+)', re.IGNORECASE)
    for m in cookie_pattern.finditer(data):
        header = m.group(1).decode()
        value = m.group(2).decode('utf-8', errors='ignore')[:500]
        key = f"{header}: {value[:50]}"
        if key not in results:
            results[key] = 0
        results[key] += 1
    
    return results

def extract_all_flows_robust(data):
    """
    Most robust approach: find all content between HTTP/1.x markers
    and extract request/response pairs.
    """
    # The mitmproxy format interleaves requests and responses
    # Let's find all "request" and "response" markers
    # Looking at the binary format header: it uses msgpack-like encoding
    
    # Actually, let's try a different approach: scan for the actual content
    # The file contains the HTML content of mitmproxy UI at the beginning,
    # then actual flow data
    
    # Find where actual flow data starts (after the UI HTML)
    # Look for the first real HTTP request
    first_get = data.find(b'GET /')
    first_connect = data.find(b'CONNECT ')
    
    print(f"First GET at offset: {first_get}")
    print(f"First CONNECT at offset: {first_connect}")
    print()
    
    # Scan the entire file for all domains
    # This is a mitmproxy flow file - each flow has:
    # - Client connect
    # - TLS handshake  
    # - Request (method, url, headers, body)
    # - Response (status, headers, body)
    
    # Let's extract by finding all domain references
    domain_pattern = re.compile(rb'([a-z0-9][-a-z0-9]*\.)+[a-z]{2,}')
    all_domains = Counter()
    for m in domain_pattern.finditer(data):
        domain = m.group().decode('utf-8', errors='ignore').lower()
        if len(domain) > 5 and not domain.endswith(('.png', '.jpg', '.gif', '.css', '.ico', '.woff', '.woff2', '.ttf', '.svg')):
            all_domains[domain] += 1
    
    print(f"Found {len(all_domains)} unique domains (by frequency):")
    for domain, count in all_domains.most_common(200):
        print(f"  {domain}: {count}")
    
    return all_domains

if __name__ == '__main__':
    print(f"Reading: {FILE}")
    print(f"Size: {os.path.getsize(FILE) / 1024 / 1024:.1f} MB")
    print("=" * 80)
    
    with open(FILE, 'rb') as f:
        data = f.read()
    
    print("\n--- STEP 1: Host headers ---")
    hosts = parse_flow_file(data)
    
    print("\n--- STEP 2: HTTP requests ---")
    requests = find_all_urls_complete(data)
    
    print("\n--- STEP 3: HTTP responses ---")
    responses = find_response_codes(data)
    
    print("\n--- STEP 4: All domains ---")
    domains = extract_all_flows_robust(data)
    
    print("\n--- STEP 5: JSON bodies with streaming keywords ---")
    jsons = find_json_bodies(data)
    for i, j in enumerate(jsons[:20]):
        print(f"\nJSON {i+1}:")
        print(f"  {j[:500]}")
    
    print("\n--- STEP 6: Embed/iframe URLs ---")
    embeds = find_embed_iframes(data)
    for url in sorted(embeds)[:50]:
        print(f"  {url[:300]}")
    
    print("\n--- STEP 7: Cookies/Auth ---")
    cookies = find_cookie_auth(data)
    for key, count in sorted(cookies.items(), key=lambda x: -x[1])[:50]:
        print(f"  [{count}x] {key}")
    
    # Save full analysis
    with open(os.path.join(OUT_DIR, "full_analysis.txt"), 'w', encoding='utf-8') as f:
        f.write(f"Total size: {len(data)} bytes\n\n")
        f.write("=== HOSTS ===\n")
        for host, count in hosts.most_common():
            f.write(f"{host}\t{count}\n")
        f.write("\n=== REQUESTS ===\n")
        for method, host, url, pos in requests:
            f.write(f"{method}\t{host}\t{url}\t{pos}\n")
        f.write("\n=== DOMAINS ===\n")
        for domain, count in domains.most_common():
            f.write(f"{domain}\t{count}\n")
        f.write("\n=== JSON BODIES ===\n")
        for j in jsons:
            f.write(j + "\n---\n")
        f.write("\n=== EMBED URLS ===\n")
        for url in sorted(embeds):
            f.write(url + "\n")
    
    print(f"\nFull analysis saved to {OUT_DIR}/full_analysis.txt")
