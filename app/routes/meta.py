from urllib.parse import unquote
from flask import Blueprint
from app.api import ALL_PROVIDERS
from app.routes.utils import respond_with, log_error
from app.mapper import map_imdb_to_all_slugs, parse_custom_id
from app.config_parser import parse_config

meta_bp = Blueprint('meta', __name__)

@meta_bp.route('/meta/<meta_type>/<meta_id>.json')
@meta_bp.route('/<lang>/meta/<meta_type>/<meta_id>.json')
@meta_bp.route('/<config_data>/meta/<meta_type>/<meta_id>.json')
@meta_bp.route('/<config_data>/<lang>/meta/<meta_type>/<meta_id>.json')
def addon_meta(meta_type, meta_id, lang=None, config_data=None):
    meta_id = unquote(meta_id)

    targets = []
    if meta_id.startswith('tt'):
        all_matches = map_imdb_to_all_slugs(meta_id)
        for slug, pname in all_matches:
            targets.append((pname, slug))
    elif meta_id.startswith('hd:'):
        result = parse_custom_id(meta_id)
        if result:
            targets.append(result)

    if not targets:
        return respond_with({'meta': {}})

    # Try all providers, prefer first successful
    for provider_name, slug in targets:
        provider = ALL_PROVIDERS.get(provider_name)
        if not provider: continue

        try:
            details = provider.get_anime_details(slug)
            if not details: continue

            meta = {
                'id': meta_id, 'type': meta_type,
                'name': details.get('title', ''),
                'description': details.get('description', ''),
                'poster': details.get('poster', ''),
                'genres': details.get('genres', []),
                'releaseInfo': details.get('year', ''), 'runtime': details.get('runtime', ''),
            }
            if details.get('type') == 'series':
                meta['videos'] = [{
                    'id': f"{meta_id}:{ep.get('season',1)}:{ep.get('episode',1)}",
                    'title': ep.get('title', f"Episode {ep.get('episode',1)}"),
                    'episode': ep.get('episode', 1), 'season': ep.get('season', 1),
                } for ep in details.get('episodes', [])]

            return respond_with({'meta': meta}, 86400)
        except Exception as e:
            log_error(e)

    return respond_with({'meta': {}})
