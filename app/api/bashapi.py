import requests, re, os
from cachetools import TTLCache, cached
from urllib.parse import quote

BASE_URL = 'https://ind.bashapi.tech'
UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36'
TIMEOUT = 15

SCRAPER_PROXY = os.getenv('SCRAPER_PROXY_URL', '')
SCRAPER_PROXY_PW = os.getenv('SCRAPER_PROXY_PASSWORD', '')

search_cache = TTLCache(maxsize=512, ttl=3600)
details_cache = TTLCache(maxsize=1024, ttl=3600)

def _proxy_url(target):
    return f"{SCRAPER_PROXY}/proxy/stream?d={quote(target, safe='')}&api_password={SCRAPER_PROXY_PW}&h_user-agent={quote(UA, safe='')}"


class BashAPIProvider:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': UA,
            'Accept': 'application/json',
        })

    def _get(self, url, **kwargs):
        target = _proxy_url(url) if SCRAPER_PROXY else url
        kwargs.setdefault('timeout', TIMEOUT)
        return self.session.get(target, **kwargs)

    @cached(search_cache)
    def search_anime(self, query: str) -> list:
        results = []
        try:
            resp = self._get(f'{BASE_URL}/home')
            data = resp.json()
            if not data.get('success'):
                return []

            seen = set()
            for section in data.get('data', {}).get('main', []):
                for item in section.get('data', []):
                    title = item.get('title', '').strip()
                    if not title or len(title) < 2:
                        continue
                    if query.lower() not in title.lower():
                        continue

                    slug = item.get('slug', '')
                    series_slug = re.sub(r'-\d+x\d+$', '', slug)
                    if series_slug in seen:
                        continue
                    seen.add(series_slug)

                    content_type = item.get('type', 'series')
                    results.append({
                        'title': title,
                        'slug': series_slug,
                        'poster': item.get('poster', ''),
                        'type': content_type,
                        'provider': 'bashapi',
                        'tmdb_rating': item.get('tmdbRating'),
                    })

        except Exception as e:
            print(f'[bashapi] search error: {e}')
        return results

    def get_home_catalog(self) -> list:
        return self.search_anime('')

    @cached(details_cache)
    def get_anime_details(self, slug: str) -> dict:
        try:
            resp = self._get(f'{BASE_URL}/series/info/{slug}')
            data = resp.json()
            if not data.get('success'):
                resp2 = self._get(f'{BASE_URL}/movie/info/{slug}')
                data2 = resp2.json()
                if data2.get('success'):
                    return self._parse_movie(data2.get('data', {}), slug)
                return None

            info = data.get('data', {})
            return self._parse_series(info, slug)

        except Exception as e:
            print(f'[bashapi] details error: {e}')
            return None

    def _parse_series(self, info, slug):
        seasons = info.get('seasons', [])
        episodes = []
        for season in seasons:
            season_num = season.get('season_no', 1)
            for ep in season.get('episodes', []):
                ep_num = ep.get('episode_no', 0)
                ep_slug = ep.get('slug', f'{slug}-{season_num}x{ep_num}')
                episodes.append({
                    'season': season_num,
                    'episode': ep_num,
                    'title': ep.get('title', f'S {season_num} | E {ep_num}'),
                    'slug': ep_slug,
                    'ep_page_url': f'{BASE_URL}/episode/{ep_slug}/',
                    'poster': ep.get('thumbnail', ''),
                    'data_post': ep_slug,
                    'data_nume': str(ep_num),
                    'data_type': 'tv',
                })

        if not episodes:
            total = info.get('totalEpisodes', 12)
            for i in range(1, total + 1):
                ep_slug = f'{slug}-1x{i}'
                episodes.append({
                    'season': 1, 'episode': i,
                    'title': f'S 1 | E {i}',
                    'slug': ep_slug,
                    'ep_page_url': f'{BASE_URL}/episode/{ep_slug}/',
                    'data_post': ep_slug,
                    'data_nume': str(i),
                    'data_type': 'tv',
                })

        return {
            'title': info.get('title', ''),
            'slug': slug,
            'poster': info.get('poster', ''),
            'type': 'series',
            'provider': 'bashapi',
            'episodes': episodes,
            'total_seasons': info.get('totalSeasons', 1),
        }

    def _parse_movie(self, data, slug):
        return {
            'title': data.get('title', '').strip(),
            'slug': slug,
            'poster': data.get('poster', ''),
            'type': 'movie',
            'provider': 'bashapi',
            'episodes': [{
                'season': 1, 'episode': 1,
                'title': 'Movie',
                'slug': slug,
                'ep_page_url': f'{BASE_URL}/episode/{slug}/',
            }],
        }

    def get_episodes(self, slug: str) -> list:
        details = self.get_anime_details(slug)
        return details.get('episodes', []) if details else []

    def get_episode_streams(self, slug: str, season: int, episode: int) -> dict:
        details = self.get_anime_details(slug)
        if not details:
            return {'streams': []}

        eps = details.get('episodes', [])
        ep_data = None
        for ep in eps:
            if ep.get('episode') == episode and ep.get('season', 1) == season:
                ep_data = ep
                break
        if not ep_data and eps:
            ep_data = eps[episode - 1] if episode <= len(eps) else None

        if not ep_data:
            return {'streams': []}

        streams = []
        data_post = ep_data.get('data_post', '')
        if data_post:
            try:
                ep_page = ep_data.get('ep_page_url', f'{BASE_URL}/episode/{data_post}/')
                resp = self._get(ep_page)
                html = resp.text

                for iframe in re.findall(r'<iframe[^>]+src=["\']([^"\']+)["\']', html):
                    if not iframe or 'about:blank' in iframe:
                        continue
                    if iframe.startswith('//'):
                        iframe = 'https:' + iframe
                    streams.append({
                        'player': self._classify(iframe),
                        'url': iframe,
                        'name': 'BashAPI',
                        'languages': [],
                    })

                for m3u8 in re.findall(r'(https?://[^\s"\'<>]+\.m3u8[^\s"\'<>]*)', html):
                    streams.append({
                        'player': 'direct_m3u8',
                        'url': m3u8,
                        'name': 'BashAPI/Direct',
                        'languages': [],
                    })

            except Exception as e:
                print(f'[bashapi] episode scrape error: {e}')

        return {'streams': streams}

    def _classify(self, url):
        u = url.lower()
        if 'zephyr' in u or 'as-cdn' in u:
            return 'zephyrflick'
        if 'gdmirrorbot' in u or 'iqsmartgames' in u:
            return 'gdmirrorbot'
        if 'vidmoly' in u:
            return 'vidmoly'
        if 'streamruby' in u:
            return 'streamruby'
        if 'dood' in u:
            return 'doodstream'
        if 'p2pplay' in u or 'strp' in u or 'upns' in u:
            return 'streamp2p'
        if 'turbovid' in u:
            return 'turbovid'
        if 'abyss' in u:
            return 'abyss'
        if 'megacloud' in u or 'mewstream' in u:
            return 'megacloud'
        if 'flixcloud' in u:
            return 'flixcloud'
        if 'hanerix' in u or 'streamhg' in u:
            return 'streamhg'
        if '.m3u8' in u:
            return 'direct_m3u8'
        return 'generic_embed'
