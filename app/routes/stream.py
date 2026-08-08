import urllib.parse
from flask import Blueprint, abort
from app.api import ALL_PROVIDERS
from app.routes.utils import respond_with, log_error
from app.mapper import map_imdb_to_all_slugs, parse_custom_id
from app.players import resolve_stream
from app.config_parser import parse_config, get_provider_from_config, get_langs_from_config

stream_bp = Blueprint('stream', __name__)


@stream_bp.route('/stream/<content_type>/<content_id>.json')
@stream_bp.route('/<lang>/stream/<content_type>/<content_id>.json')
@stream_bp.route('/<config_data>/stream/<content_type>/<content_id>.json')
@stream_bp.route('/<config_data>/<lang>/stream/<content_type>/<content_id>.json')
def addon_stream(content_type, content_id, lang=None, config_data=None):
    content_id = urllib.parse.unquote(content_id)
    config = parse_config(config_data or '')
    enabled_providers = get_provider_from_config(config)
    enabled_langs = get_langs_from_config(config)
    max_timeout = int(config.get('timeout', 15))
    max_streams = int(config.get('max', 15))

    parts = content_id.split(':')
    base_id = parts[0]

    # Parse season/episode from ID
    targets = []  # list of (provider_name, slug)

    if base_id.startswith('tt'):
        imdb_id = base_id
        season = int(parts[1]) if len(parts) > 1 else 1
        episode = int(parts[2]) if len(parts) > 2 else 1

        # Get ALL providers matching this IMDB
        all_matches = map_imdb_to_all_slugs(imdb_id)
        for slug, pname in all_matches:
            if pname in enabled_providers:
                targets.append((pname, slug, season, episode))
    elif base_id == 'hd':
        id_parts = content_id.split(':')
        if len(id_parts) >= 3:
            targets.append((
                id_parts[1], id_parts[2],
                int(id_parts[3]) if len(id_parts) > 3 else 1,
                int(id_parts[4]) if len(id_parts) > 4 else 1,
            ))
        else:
            return respond_with({'streams': []})
    else:
        return respond_with({'streams': []})

    if not targets:
        return respond_with({'streams': []})

    # Collect streams from ALL matching providers
    all_streams = []

    for pname, slug, season, episode in targets:
        provider = ALL_PROVIDERS.get(pname)
        if not provider: continue

        try:
            data = provider.get_episode_streams(slug, season, episode)
            for sd in data.get('streams', []):
                # Language filter
                player_langs = [l.lower() for l in sd.get('languages', [])]
                if player_langs and enabled_langs:
                    matches = any(pl in enabled_langs for pl in player_langs)
                    if not matches:
                        continue

                try:
                    resolved = resolve_stream(sd)
                    all_streams.extend(resolved)
                except Exception as e:
                    print(f'[stream] resolve error for {pname}: {e}')
        except Exception as e:
            print(f'[stream] provider error {pname}: {e}')

    # Deduplicate and format
        final = []
        seen = set()
        for s in all_streams[:max_streams]:
            key = s.get('url', '')
            if not key or key in seen: continue
            seen.add(key)

            stream_obj = {
                'title': s.get('title', 'Stream'),
                'behaviorHints': s.get('behaviorHints', {'notWebReady': True}),
                'name': s.get('name', 'Stream'),
                'url': s['url'],
            }
            if s.get('subtitles'): stream_obj['subtitles'] = s['subtitles']

            final.append(stream_obj)

    print(f'[stream] {content_id} -> {len(final)} streams from {len(targets)} providers')
    return respond_with({'streams': final})
