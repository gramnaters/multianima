import requests
from typing import Optional
from cachetools import TTLCache
from config import Config
from app.database import db

search_cache = TTLCache(maxsize=1000, ttl=3600)
slug_to_imdb = TTLCache(maxsize=2000, ttl=3600)
imdb_to_slug = TTLCache(maxsize=2000, ttl=3600)
failed_cache = TTLCache(maxsize=500, ttl=3600)


def _has_tmdb() -> bool:
    return bool(Config.TMDB_API_KEY and Config.TMDB_API_KEY != 'your_tmdb_api_key_here')


def get_imdb_from_tmdb(tmdb_id: str, content_type: str) -> Optional[str]:
    if not _has_tmdb(): return None
    mt = 'tv' if content_type == 'series' else 'movie'
    try:
        r = requests.get(f'https://api.themoviedb.org/3/{mt}/{tmdb_id}/external_ids', params={'api_key': Config.TMDB_API_KEY}, timeout=10)
        r.raise_for_status()
        return r.json().get('imdb_id')
    except: return None


def search_tmdb(title: str, content_type: str) -> Optional[dict]:
    if not _has_tmdb(): return None
    mt = 'tv' if content_type == 'series' else 'movie'
    try:
        r = requests.get(f'https://api.themoviedb.org/3/search/{mt}', params={'api_key': Config.TMDB_API_KEY, 'query': title}, timeout=10)
        r.raise_for_status()
        results = r.json().get('results', [])
        return results[0] if results else None
    except: return None


def get_tmdb_from_imdb(imdb_id: str) -> Optional[dict]:
    if not _has_tmdb(): return None
    try:
        r = requests.get(f'https://api.themoviedb.org/3/find/{imdb_id}', params={'api_key': Config.TMDB_API_KEY, 'external_source': 'imdb_id'}, timeout=10)
        r.raise_for_status()
        data = r.json()
        if data.get('tv_results'):
            result = data['tv_results'][0]
            result['media_type'] = 'series'
            return result
        if data.get('movie_results'):
            result = data['movie_results'][0]
            result['media_type'] = 'movie'
            return result
    except: pass
    return None


def map_slug_to_imdb(slug: str, title: str, content_type: str, provider: str = '') -> Optional[str]:
    cache_key = f'{provider}:{slug}'
    if cache_key in slug_to_imdb: return slug_to_imdb[cache_key]

    mapping = db.get_mapping(slug)
    if mapping and mapping[1]:
        slug_to_imdb[cache_key] = mapping[1]
        return mapping[1]

    if not _has_tmdb():
        return None

    result = search_tmdb(title, content_type)
    if not result: return None

    tmdb_id = str(result['id'])
    imdb_id = get_imdb_from_tmdb(tmdb_id, content_type)
    if imdb_id:
        db.set_mapping(slug, tmdb_id, imdb_id, provider)
        slug_to_imdb[cache_key] = imdb_id
        return imdb_id
    return None


def map_imdb_to_slug(imdb_id: str) -> Optional[tuple]:
    """Return first matching (slug, provider) for an IMDB ID"""
    results = map_imdb_to_all_slugs(imdb_id)
    return results[0] if results else None


def map_imdb_to_all_slugs(imdb_id: str) -> list:
    """Return ALL matching (slug, provider) tuples for an IMDB ID across all providers."""
    all_cache_key = f'all:{imdb_id}'
    if all_cache_key in imdb_to_slug: return imdb_to_slug[all_cache_key]

    if not _has_tmdb():
        return []

    tmdb_details = get_tmdb_from_imdb(imdb_id)
    if not tmdb_details:
        failed_cache[imdb_id] = True; db.add_failed(imdb_id)
        return []

    title = tmdb_details.get('title') or tmdb_details.get('name', '')
    if not title:
        failed_cache[imdb_id] = True; db.add_failed(imdb_id)
        return []

    from app.api import ALL_PROVIDERS
    results = []

    # Try animelok FIRST (best provider), then others
    provider_order = ['animelok'] + [p for p in ALL_PROVIDERS if p != 'animelok']
    for pname in provider_order:
        if len(results) >= 3: break  # enough providers
        provider = ALL_PROVIDERS.get(pname)
        if not provider: continue
        try:
            items = provider.search_anime(title)
            for item in items:
                slug = item['slug']
                db.set_mapping(slug, str(tmdb_details['id']), imdb_id, pname)
                results.append((slug, pname))
                break  # one per provider
        except Exception as e:
            print(f'[mapper] {pname}: {e}')

    if results:
        imdb_to_slug[all_cache_key] = results
        return results

    failed_cache[imdb_id] = True; db.add_failed(imdb_id)
    return []


def make_custom_id(provider: str, slug: str) -> str:
    """Fallback ID when TMDB is not available: hd:provider:slug"""
    return f'hd:{provider}:{slug}'


def parse_custom_id(custom_id: str) -> Optional[tuple]:
    """Parse hd:provider:slug into (provider, slug)"""
    parts = custom_id.split(':', 2)
    if len(parts) == 3 and parts[0] == 'hd':
        return (parts[1], parts[2])
    return None
