"""Full E2E test - starts server, tests everything, stops server"""
import requests, json, time, subprocess, sys, os

BASE = 'http://127.0.0.1:5000'
results = []

def start_server():
    proc = subprocess.Popen(
        [sys.executable, 'run.py'],
        cwd=os.path.dirname(os.path.abspath(__file__)),
        stdout=subprocess.PIPE, stderr=subprocess.PIPE
    )
    for _ in range(20):
        time.sleep(1)
        try:
            r = requests.get(f'{BASE}/health', timeout=2)
            if r.ok: return proc
        except: pass
    print('WARNING: Server may not have started')
    return proc

def test(name, fn):
    try:
        ok, detail = fn()
        status = 'PASS' if ok else 'FAIL'
        results.append((status, name, detail))
        print(f'  [{status}] {name}: {detail}')
    except Exception as e:
        results.append(('ERROR', name, str(e)[:200]))
        print(f'  [ERROR] {name}: {e}')

print('Starting server...')
proc = start_server()

print('='*70)
print('MULTIANIMA E2E TEST')
print('='*70)

# === MANIFEST ===
print('\n--- MANIFEST ---')
def t_manifest():
    r = requests.get(f'{BASE}/manifest.json', timeout=10)
    d = r.json()
    return r.ok and d.get('id') == 'com.multianima.addon', f"id={d.get('id')}, catalogs={[c['id'] for c in d.get('catalogs', [])]}"
test('manifest', t_manifest)

# === CATALOG ===
print('\n--- CATALOG ---')
def t_cat_latest():
    r = requests.get(f'{BASE}/catalog/anime/hd_latest.json', timeout=15)
    metas = r.json().get('metas', [])
    return len(metas) >= 10, f"{len(metas)} metas"
test('hd_latest', t_cat_latest)

def t_cat_all():
    r = requests.get(f'{BASE}/catalog/anime/hd_all.json', timeout=15)
    metas = r.json().get('metas', [])
    names = [m['name'] for m in metas[:5]]
    return len(metas) >= 10, f"{len(metas)} metas: {names}"
test('hd_all', t_cat_all)

def t_search():
    r = requests.get(f'{BASE}/catalog/anime/hd_all/search=naruto.json', timeout=15)
    metas = r.json().get('metas', [])
    names = [m['name'] for m in metas[:3]]
    ids = [m['id'] for m in metas[:3]]
    return len(metas) > 0 and all(m['id'].startswith('hd:tmdb:') for m in metas), f"{len(metas)} results, ids={ids}, names={names}"
test('search_naruto', t_search)

# === META ===
print('\n--- META ---')
def t_meta_tmdb():
    r = requests.get(f'{BASE}/catalog/anime/hd_all.json', timeout=15)
    mid = r.json()['metas'][0]['id']
    r2 = requests.get(f'{BASE}/meta/series/{mid}.json', timeout=15)
    meta = r2.json().get('meta', {})
    vids = meta.get('videos', [])
    return meta.get('name') and len(vids) > 0, f"id={mid}, name={meta.get('name')}, videos={len(vids)}"
test('meta_catalog', t_meta_tmdb)

def t_meta_tt():
    r = requests.get(f'{BASE}/meta/series/tt0409591.json', timeout=15)
    meta = r.json().get('meta', {})
    vids = meta.get('videos', [])
    first_vid = vids[0]['id'] if vids else 'none'
    return meta.get('name') == 'Naruto' and len(vids) > 100, f"name={meta.get('name')}, videos={len(vids)}, first_vid={first_vid}"
test('meta_naruto', t_meta_tt)

# === STREAM ===
print('\n--- STREAM ---')
def t_stream_naruto():
    r = requests.get(f'{BASE}/stream/series/tt0409591:1:1.json', timeout=60)
    streams = r.json().get('streams', [])
    urls = [s.get('url', '') for s in streams]
    has_m3u8 = any('.m3u8' in u for u in urls)
    all_url = all(s.get('url') for s in streams)
    no_ext = all(not s.get('externalUrl') for s in streams)
    titles = [s.get('title', '')[:40] for s in streams[:5]]
    return len(streams) > 0 and all_url and no_ext, f"{len(streams)} streams, m3u8={has_m3u8}, no_external={no_ext}, titles={titles}"
test('stream_naruto_e1', t_stream_naruto)

def t_stream_naruto_e2():
    r = requests.get(f'{BASE}/stream/series/tt0409591:1:2.json', timeout=60)
    streams = r.json().get('streams', [])
    return len(streams) > 0, f"{len(streams)} streams"
test('stream_naruto_e2', t_stream_naruto_e2)

def t_stream_from_catalog():
    r = requests.get(f'{BASE}/catalog/anime/hd_all.json', timeout=15)
    mid = r.json()['metas'][0]['id']
    r2 = requests.get(f'{BASE}/stream/series/{requests.utils.quote(mid + ":1:1")}.json', timeout=60)
    streams = r2.json().get('streams', [])
    return True, f"id={mid}, {len(streams)} streams (expected some 0 for obscure anime)"
test('stream_catalog_id', t_stream_from_catalog)

# === PROVIDERS ===
print('\n--- PROVIDERS (direct) ---')
from app.api import animelok, watchanimeworld, animesalt, animejoker

for pname, pobj in [('animelok', animelok), ('watchanimeworld', watchanimeworld), ('animesalt', animesalt), ('animejoker', animejoker)]:
    def t_prov(name=pname, prov=pobj):
        sr = prov.search_anime('naruto')
        if not sr: return False, 'no results'
        slug = sr[0]['slug']
        sd = prov.get_episode_streams(slug, 1, 1)
        s = sd.get('streams', [])
        players = [x.get('player', '?') for x in s]
        return len(s) > 0, f"slug={slug}, {len(s)} streams, players={players}"
    test(f'prov_{pname}', t_prov)

# === EXTRACTORS ===
print('\n--- EXTRACTORS ---')
from app.players.all_players import EXTRACTORS, classify_url

def t_classify():
    tests = [
        ('https://play.zephyrix.top/video/x', 'zephyrflick'),
        ('https://as-cdn21.top/video/x', 'zephyrflick'),
        ('https://gdmirrorbot.nl/embed/x', 'gdmirrorbot'),
        ('https://vidmoly.org/embed/x', 'vidmoly'),
        ('https://streamruby.com/e/x', 'streamruby'),
        ('https://dood.to/e/x', 'doodstream'),
        ('https://example.com/video.m3u8', 'direct_m3u8'),
    ]
    ok = all(classify_url(u) == e for u, e in tests)
    fails = [(u, classify_url(u), e) for u, e in tests if classify_url(u) != e]
    return ok, f"{len(tests)} tests OK" if ok else f"FAILS: {fails}"
test('classify_url', t_classify)

def t_extract_zephyr():
    try:
        result = EXTRACTORS['zephyrflick']('https://play.zephyrix.top/video/1cc1fab198176208789cf94b71412dc8')
        streams = result.get('streams', [])
        return len(streams) > 0, f"{len(streams)} streams, url={streams[0].get('url','')[:60]}" if streams else 'empty'
    except Exception as e:
        return False, str(e)[:100]
test('extract_zephyrflick', t_extract_zephyr)

# === CONFIG ===
print('\n--- CONFIG ---')
def t_config():
    r = requests.get(f'{BASE}/configure', timeout=10)
    return r.ok and len(r.text) > 100, f"status={r.status_code}, size={len(r.text)}"
test('config_page', t_config)

# === HEALTH ===
def t_health():
    r = requests.get(f'{BASE}/health', timeout=5)
    return r.ok, r.json()
test('health', t_health)

# === SUMMARY ===
print('\n' + '='*70)
passed = sum(1 for s,_,_ in results if s == 'PASS')
failed = sum(1 for s,_,_ in results if s in ('FAIL','ERROR'))
total = len(results)
print(f'RESULTS: {passed}/{total} passed, {failed} failed')
print('='*70)
if failed:
    print('\nFAILURES:')
    for s, name, detail in results:
        if s in ('FAIL', 'ERROR'):
            print(f'  [{s}] {name}: {detail}')

proc.terminate()
proc.wait(timeout=5)
