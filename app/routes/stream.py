import urllib.parse, requests
from flask import Blueprint, abort
from cachetools import TTLCache
from app.api import ALL_PROVIDERS
from app.routes.utils import respond_with, log_error
from app.players import resolve_stream, PLAYER_NAMES
from app.config_parser import parse_config, get_provider_from_config, get_langs_from_config, get_quality_from_config, is_hide_non_seekable

stream_bp = Blueprint('stream', __name__)
tmdb_title_cache = TTLCache(maxsize=500, ttl=3600)


PROVIDER_DISPLAY = {
    'animelok': 'AnimeLok',
    'watchanimeworld': 'AnimeWorld',
    'animesalt': 'AnimeSalt',
    'animejoker': 'AnimeJoker',
    'desidubanime': 'DesiDub',
    'bashapi': 'BashAPI',
}


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
                break
        except: pass
    return results


def _quality_from_name(name):
    name_lower = name.lower()
    if '2160' in name_lower or '4k' in name_lower: return '4K'
    if '1080' in name_lower: return '1080p'
    if '720' in name_lower: return '720p'
    if '480' in name_lower: return '480p'
    if '360' in name_lower: return '360p'
    return ''


def _referer_for_url(url):
    """Return the correct Referer header for a stream URL"""
    if 'zephyrix' in url or 'zephyrflick' in url:
        return 'https://play.zephyrix.top/'
    if 'anvod' in url or 'af0' in url:
        return 'https://bato.to/'
    if 'uwucdn' in url or 'vault-0' in url:
        return 'https://pahe.host/'
    if 'hsastream' in url:
        return 'https://animevilla.org/'
    from urllib.parse import urlparse
    parsed = urlparse(url)
    return f'{parsed.scheme}://{parsed.hostname}/'


def _make_title(provider_name, player_key, extra=''):
    site = PROVIDER_DISPLAY.get(provider_name, provider_name)
    player = PLAYER_NAMES.get(player_key, player_key)
    parts = [site, player]
    if extra:
        parts.append(extra)
    return ' / '.join(parts)


@stream_bp.route('/stream/<content_type>/<content_id>.json')
@stream_bp.route('/<lang>/stream/<content_type>/<content_id>.json')
@stream_bp.route('/<config_data>/stream/<content_type>/<content_id>.json')
@stream_bp.route('/<config_data>/<lang>/stream/<content_type>/<content_id>.json')
def addon_stream(content_type, content_id, lang=None, config_data=None):
    content_id = urllib.parse.unquote(content_id)
    config = parse_config(config_data or '')
    enabled_providers = get_provider_from_config(config)
    enabled_langs = get_langs_from_config(config)
    enabled_qualities = get_quality_from_config(config)

    parts = content_id.split(':')
    season, episode = 1, 1

    if len(parts) >= 3 and parts[-2].isdigit() and parts[-1].isdigit():
        season = int(parts[-2])
        episode = int(parts[-1])
        base_id_parts = parts[:-2]
    else:
        base_id_parts = parts

    base_id = ':'.join(base_id_parts)

    tmdb_id = None
    if base_id.startswith('tmdb:'):
        tmdb_id = base_id.replace('tmdb:', '')
    elif base_id.startswith('hd:tmdb:'):
        tmdb_id = base_id.replace('hd:tmdb:', '')
    elif base_id.startswith('tt'):
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

    title = _get_title_from_tmdb(tmdb_id)
    if not title:
        return respond_with({'streams': []})

    provider_slugs = _search_providers_for_title(title, enabled_providers)
    if not provider_slugs:
        return respond_with({'streams': []})

    # Collect streams from providers — keep provider info
    raw_streams = []
    for pname, slug in provider_slugs[:5]:
        provider = ALL_PROVIDERS.get(pname)
        if not provider: continue
        try:
            data = provider.get_episode_streams(slug, season, episode)
            for sd in data.get('streams', []):
                sd['_provider'] = pname
                raw_streams.append(sd)
        except Exception as e:
            print(f'[stream] provider {pname}: {e}')

    # Resolve all streams
    final = []
    seen = set()
    for sd in raw_streams:
        pname = sd.get('_provider', 'unknown')
        player_key = sd.get('player', 'generic_embed')

        try:
            resolved_list = resolve_stream(sd)
        except Exception as e:
            print(f'[stream] resolve error: {e}')
            continue

        for resolved in resolved_list:
            url = resolved.get('url', '')
            if not url or url in seen:
                continue
            seen.add(url)

            quality = _quality_from_name(url)
            display_title = _make_title(pname, player_key, quality)

            stream_obj = {
                'title': display_title,
                'name': display_title,
                'url': url,
                'behaviorHints': {
                    'notWebReady': False,
                    'bingeGroup': f'multianima-{pname}',
                    'proxyHeaders': {
                        'request': {
                            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36',
                            'Referer': _referer_for_url(url),
                        }
                    }
                },
            }
            if resolved.get('subtitles'):
                stream_obj['subtitles'] = resolved['subtitles']
            final.append(stream_obj)

    print(f'[stream] {content_id} => {len(final)} streams')
    return respond_with({'streams': final})
