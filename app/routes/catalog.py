import urllib.parse
from flask import Blueprint, abort, request
from app.api import ALL_PROVIDERS
from app.mapper import map_slug_to_imdb, make_custom_id
from app.routes.utils import respond_with, log_error
from app.config_parser import parse_config, get_provider_from_config

catalog_bp = Blueprint('catalog', __name__)


@catalog_bp.route('/catalog/<catalog_type>/<catalog_id>.json')
@catalog_bp.route('/catalog/<catalog_type>/<catalog_id>/search=<search>.json')
@catalog_bp.route('/<lang>/catalog/<catalog_type>/<catalog_id>.json')
@catalog_bp.route('/<lang>/catalog/<catalog_type>/<catalog_id>/search=<search>.json')
@catalog_bp.route('/<config_data>/catalog/<catalog_type>/<catalog_id>.json')
@catalog_bp.route('/<config_data>/catalog/<catalog_type>/<catalog_id>/search=<search>.json')
@catalog_bp.route('/<config_data>/<lang>/catalog/<catalog_type>/<catalog_id>.json')
@catalog_bp.route('/<config_data>/<lang>/catalog/<catalog_type>/<catalog_id>/search=<search>.json')
def addon_catalog(catalog_type, catalog_id, search=None, lang=None, config_data=None):
    config = parse_config(config_data or '')
    enabled_providers = get_provider_from_config(config)

    if catalog_id not in ['hd_all', 'hd_latest']:
        abort(404)

    try:
        all_results = []
        if search:
            search = urllib.parse.unquote(search)
            for pname in enabled_providers:
                provider = ALL_PROVIDERS.get(pname)
                if not provider: continue
                try:
                    items = provider.search_anime(search)
                    all_results.extend(items)
                except: pass
        else:
            for pname in enabled_providers:
                provider = ALL_PROVIDERS.get(pname)
                if not provider: continue
                try:
                    items = provider.get_home_catalog()
                    all_results.extend(items)
                except: pass

        metas = []
        seen = set()
        for item in all_results:
            slug = item.get('slug', '')
            title = item.get('title', '')
            provider_name = item.get('provider', '')
            cache_key = f'{provider_name}:{slug}'.lower()
            if cache_key in seen: continue
            seen.add(cache_key)

            imdb_id = map_slug_to_imdb(slug, title, item.get('type', 'series'), provider_name)
            meta_id = imdb_id if imdb_id else make_custom_id(provider_name, slug)

            metas.append({
                'id': meta_id, 'type': item.get('type', 'series'),
                'name': title, 'poster': item.get('poster', ''),
            })

        print(f'[catalog] Returned {len(metas)} metas (search={search})')
        return respond_with({'metas': metas}, 3600)

    except Exception as e:
        log_error(e)
        return respond_with({'metas': []}, 3600)
