"""Use mitmproxy's built-in flow reader to parse every single flow."""
import os
import sys
import json
from collections import defaultdict, Counter
from datetime import datetime

# Suppress mitmproxy output noise
import logging
logging.disable(logging.CRITICAL)

FILE = os.path.join(os.path.dirname(__file__), "all traffic")
OUT_DIR = os.path.join(os.path.dirname(__file__), "traffic_analysis_full")
os.makedirs(OUT_DIR, exist_ok=True)

from mitmproxy.io import FlowReader

def main():
    print(f"Reading: {FILE}")
    print(f"Size: {os.path.getsize(FILE) / 1024 / 1024:.1f} MB")
    print("=" * 80)
    
    flows = []
    flow_count = 0
    error_count = 0
    
    with open(FILE, "rb") as f:
        reader = FlowReader(f)
        try:
            for flow in reader.stream():
                flow_count += 1
                try:
                    flows.append(flow)
                    if flow_count % 100 == 0:
                        print(f"  Processed {flow_count} flows...")
                except Exception as e:
                    error_count += 1
        except Exception as e:
            print(f"Error reading flows: {e}")
    
    print(f"\nTotal flows: {flow_count}")
    print(f"Errors: {error_count}")
    print(f"Successfully parsed: {len(flows)}")
    print("=" * 80)
    
    # Categorize
    hosts = Counter()
    urls = []
    response_bodies = {}
    request_bodies = {}
    all_requests = []
    all_responses = []
    video_urls = set()
    json_responses = []
    embed_urls = set()
    api_calls = []
    
    for flow in flows:
        try:
            if flow.request:
                req = flow.request
                host = req.host or ""
                port = req.port or ""
                method = req.method or ""
                path = req.path or ""
                scheme = req.scheme or "http"
                
                full_url = f"{scheme}://{host}:{port}{path}" if port and port != 80 and port != 443 else f"{scheme}://{host}{path}"
                
                hosts[host] += 1
                all_requests.append({
                    'method': method,
                    'host': host,
                    'port': port,
                    'path': path,
                    'url': full_url,
                    'headers': dict(req.headers) if req.headers else {},
                })
                urls.append(full_url)
                
                # Check for video/streaming keywords
                url_lower = full_url.lower()
                if any(kw in url_lower for kw in ['.m3u8', '.ts', '.mp4', '.mpd', 'manifest', 'playlist', 'stream', 'video', 'media']):
                    video_urls.add(full_url)
                
                # Check for embed/iframe
                if any(kw in url_lower for kw in ['embed', 'iframe', 'player']):
                    embed_urls.add(full_url)
                
                # Check for API calls
                if any(kw in url_lower for kw in ['/api/', '/v1/', '/v2/', 'graphql', 'source', 'episode']):
                    api_calls.append(full_url)
                
                # Get request body
                if req.content:
                    try:
                        body = req.content.decode('utf-8', errors='ignore')
                        if len(body) > 10:
                            request_bodies[full_url] = body[:5000]
                    except:
                        pass
                        
            if flow.response:
                resp = flow.response
                status = resp.status_code or 0
                content_type = resp.headers.get('content-type', '') if resp.headers else ''
                
                all_responses.append({
                    'status': status,
                    'content_type': content_type,
                    'url': urls[-1] if urls else '',
                })
                
                if resp.content:
                    try:
                        body = resp.content.decode('utf-8', errors='ignore')
                        if 'json' in content_type.lower() or body.strip().startswith('{') or body.strip().startswith('['):
                            # Check for streaming-related JSON
                            if any(kw in body.lower() for kw in ['m3u8', 'stream', 'video', 'source', 'file', 'url', 'link', 'embed', 'episode', 'server', 'quality', 'hls', 'mp4', 'iframe', 'media', 'source', 'data']):
                                json_responses.append({
                                    'url': urls[-1] if urls else '',
                                    'status': status,
                                    'body': body[:10000]
                                })
                        response_bodies[urls[-1] if urls else ''] = body[:5000]
                    except:
                        pass
        except Exception as e:
            error_count += 1
    
    # Print results
    print(f"\n{'='*80}")
    print(f"UNIQUE HOSTS ({len(hosts)} total):")
    print(f"{'='*80}")
    for host, count in hosts.most_common():
        print(f"  {count:6d}  {host}")
    
    print(f"\n{'='*80}")
    print(f"VIDEO/STREAM URLs ({len(video_urls)} unique):")
    print(f"{'='*80}")
    for url in sorted(video_urls):
        print(f"  {url[:300]}")
    
    print(f"\n{'='*80}")
    print(f"EMBED/IFRAME URLs ({len(embed_urls)} unique):")
    print(f"{'='*80}")
    for url in sorted(embed_urls):
        print(f"  {url[:300]}")
    
    print(f"\n{'='*80}")
    print(f"API/EPISODE/SOURCE CALLS ({len(api_calls)} unique):")
    print(f"{'='*80}")
    for url in sorted(set(api_calls)):
        print(f"  {url[:300]}")
    
    print(f"\n{'='*80}")
    print(f"JSON RESPONSES WITH STREAMING DATA ({len(json_responses)} total):")
    print(f"{'='*80}")
    for i, jr in enumerate(json_responses[:50]):
        print(f"\n--- JSON Response {i+1} [{jr['status']}] ---")
        print(f"URL: {jr['url'][:200]}")
        print(f"Body: {jr['body'][:1000]}")
    
    print(f"\n{'='*80}")
    print(f"REQUEST BODIES ({len(request_bodies)} with content):")
    print(f"{'='*80}")
    for url, body in list(request_bodies.items())[:30]:
        if any(kw in body.lower() for kw in ['episode', 'source', 'stream', 'video', 'server', 'anime']):
            print(f"\n--- Request: {url[:200]} ---")
            print(f"Body: {body[:2000]}")
    
    # Save everything
    with open(os.path.join(OUT_DIR, "all_hosts.txt"), 'w') as f:
        for host, count in hosts.most_common():
            f.write(f"{host}\t{count}\n")
    
    with open(os.path.join(OUT_DIR, "all_urls.txt"), 'w') as f:
        for url in sorted(set(urls)):
            f.write(url + "\n")
    
    with open(os.path.join(OUT_DIR, "video_urls.txt"), 'w') as f:
        for url in sorted(video_urls):
            f.write(url + "\n")
    
    with open(os.path.join(OUT_DIR, "embed_urls.txt"), 'w') as f:
        for url in sorted(embed_urls):
            f.write(url + "\n")
    
    with open(os.path.join(OUT_DIR, "api_calls.txt"), 'w') as f:
        for url in sorted(set(api_calls)):
            f.write(url + "\n")
    
    with open(os.path.join(OUT_DIR, "json_responses.json"), 'w') as f:
        json.dump(json_responses, f, indent=2, default=str)
    
    with open(os.path.join(OUT_DIR, "request_bodies.json"), 'w') as f:
        json.dump(request_bodies, f, indent=2, default=str)
    
    with open(os.path.join(OUT_DIR, "all_requests.json"), 'w') as f:
        json.dump(all_requests, f, indent=2, default=str)
    
    with open(os.path.join(OUT_DIR, "all_responses.json"), 'w') as f:
        json.dump(all_responses, f, indent=2, default=str)
    
    print(f"\nSaved all data to {OUT_DIR}/")
    print("Files: all_hosts.txt, all_urls.txt, video_urls.txt, embed_urls.txt, api_calls.txt,")
    print("       json_responses.json, request_bodies.json, all_requests.json, all_responses.json")

if __name__ == '__main__':
    main()
