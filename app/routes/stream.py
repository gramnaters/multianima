import urllib.parse, requests
from flask import Blueprint, abort
from cachetools import TTLCache
from app.api import ALL_PROVIDERS
from app.routes.utils import respond_with, log_error
from app.players import resolve_stream
from app.config_parser import parse_config, get_provider_from_config, get_langs_from_config

stream_bp = Blueprint('stream', __name__)
tmdb_title_cache = TTLCache(maxsize=500, ttl=3600)


def _tmdb_key():
    from config import Config
    return Config.TMDB_API_KEY or ''


def _get_title_from_tmdb(tmdb_id):
    key = f'title:{tmdb_id}'
    if key in tmdb_title_cache: return tmdb_title_cache[key]
    try:
        r = requests.get(f'https://api.themoviedb.org/3/tv/{tmdb_id}',
                        params={'api_key': _tmdb_key()}, timeout=10)
        r.raise_for_status()
        title = r.json().get('name', '') or r.json().get('original_name', '')
        tmdb_title_cache[key] = title
        return title
    except:
        return ''


def _search_providers_for_title(title, enabled_providers):
    """Search anime sites by title, return list of (provider_name, slug)"""
    results = []
    for pname in enabled_providers:
        provider = ALL_PROVIDERS.get(pname)
        if not provider: continue
        try:
            items = provider.search_anime(title)
            for item in items:
                results.append((pname, item['slug']))
                break  # One match per provider
        except: pass
    return results


@stream_bp.route('/stream/<content_type>/<content_id>.json')
@stream_bp.route('/<lang>/stream/<content_type>/<content_id>.json')
@stream_bp.route('/<config_data>/stream/<content_type>/<content_id>.json')
@stream_bp.route('/<config_data>/<lang>/stream/<content_type>/<content_id>.json')
def addon_stream(content_type, content_id, lang=None, config_data=None):
    content_id = urllib.parse.unquote(content_id)
    config = parse_config(config_data or '')
    enabled_providers = get_provider_from_config(config)
    enabled_langs = get_langs_from_config(config)
    max_streams = int(config.get('max', 15))

    parts = content_id.split(':')
    season, episode = 1, 1

    # Parse season/episode from end of ID
    if len(parts) >= 3 and parts[-2].isdigit() and parts[-1].isdigit():
        season = int(parts[-2])
        episode = int(parts[-1])
        base_id_parts = parts[:-2]
    else:
        base_id_parts = parts

    base_id = ':'.join(base_id_parts)

    # Get TMDB ID from the id
    tmdb_id = None
    if base_id.startswith('tmdb:'):
        tmdb_id = base_id.replace('tmdb:', '')
    elif base_id.startswith('hd:tmdb:'):
        tmdb_id = base_id.replace('hd:tmdb:', '')
    elif base_id.startswith('tt'):
        # IMDB → TMDB lookup
        try:
            r = requests.get('https://api.themoviedb.org/3/find/' + base_id,
                            params={'api_key': _tmdb_key(), 'external_source': 'imdb_id'}, timeout=10)
            data = r.json()
            results = data.get('tv_results', []) or data.get('movie_results', [])
            if results:
                tmdb_id = str(results[0]['id'])
        except: pass

    if not tmdb_id:
        return respond_with({'streams': []})

    # Get title from TMDB
    title = _get_title_from_tmdb(tmdb_id)
    if not title:
        return respond_with({'streams': []})

    # Search anime sites for this title
    provider_slugs = _search_providers_for_title(title, enabled_providers)
    if not provider_slugs:
        return respond_with({'streams': []})

    # Collect streams from ALL matching providers
    all_streams = []
    for pname, slug in provider_slugs[:3]:
        provider = ALL_PROVIDERS.get(pname)
        if not provider: continue
        try:
            data = provider.get_episode_streams(slug, season, episode)
            for sd in data.get('streams', []):
                player_langs = [l.lower() for l in sd.get('languages', [])]
                if player_langs and enabled_langs:
                    if not any(pl in enabled_langs for pl in player_langs):
                        continue
                try:
                    resolved = resolve_stream(sd)
                    all_streams.extend(resolved)
                except Exception as e:
                    print(f'[stream] resolve: {e}')
        except Exception as e:
            print(f'[stream] provider {pname}: {e}')

    # Deduplicate
    final = []
    seen = set()
    for s in all_streams[:max_streams]:
        key = s.get('url', '')
        if not key or key in seen: continue
        seen.add(key)
        stream_obj = {
            'title': s.get('title', 'Stream'),
            'name': s.get('name', 'Stream'),
            'url': s['url'],
            'behaviorHints': {
                'notWebReady': False,
                'bingeGroup': s.get('name', 'multianima'),
                'proxyHeaders': {
                    'request': {
                        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                    }
                }
            },
        }
        if s.get('subtitles'):
            stream_obj['subtitles'] = s['subtitles']
        final.append(stream_obj)

    print(f'[stream] {content_id} => {len(final)} streams')
    return respond_with({'streams': final})
