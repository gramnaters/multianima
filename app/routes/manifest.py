from flask import Blueprint, request
from .utils import respond_with
from app.config_parser import parse_config, encode_config

manifest_bp = Blueprint('manifest', __name__)

BASE_MANIFEST = {
    'id': 'com.multianima.addon',
    'version': '2.0.0',
    'name': 'Multianima',
    'description': 'Stream Hindi dubbed anime from multiple providers with quality and language filters.',
    'logo': 'https://raw.githubusercontent.com/gramnaters/multianima/main/static/favicon.ico',
    'types': ['movie', 'series'],
    'idPrefixes': ['tt', 'tmdb:'],
    'catalogs': [
        {'type': 'series', 'id': 'hd_all', 'name': 'Hindi Dub Anime', 'extra': [
            {'name': 'search', 'isRequired': True}, {'name': 'skip', 'isRequired': False},
        ]},
        {'type': 'series', 'id': 'hd_latest', 'name': 'Latest Releases'},
    ],
    'behaviorHints': {'configurable': True, 'configurationRequired': False},
    'resources': [
        {'name': 'catalog', 'types': ['series', 'movie']},
        {'name': 'meta', 'types': ['series', 'movie']},
        {'name': 'stream', 'types': ['series', 'movie']},
    ],
    'config': [
        # Provider sources
        {'key': 'source_animelok', 'type': 'checkbox', 'title': 'AnimeLok', 'default': 'checked'},
        {'key': 'source_watchanimeworld', 'type': 'checkbox', 'title': 'WatchAnimeWorld', 'default': 'checked'},
        {'key': 'source_animesalt', 'type': 'checkbox', 'title': 'AnimeSalt', 'default': 'checked'},
        {'key': 'source_animejoker', 'type': 'checkbox', 'title': 'AnimeJoker', 'default': 'checked'},
        {'key': 'source_desidubanime', 'type': 'checkbox', 'title': 'DesiDubAnime', 'default': 'checked'},
        {'key': 'source_bashapi', 'type': 'checkbox', 'title': 'BashAPI', 'default': 'unchecked'},
        {'key': 'source_animevilla', 'type': 'checkbox', 'title': 'AnimeVilla', 'default': 'unchecked'},
        {'key': 'source_aniflix', 'type': 'checkbox', 'title': 'Aniflix (needs TRAWL)', 'default': 'unchecked'},
        # Quality
        {'key': 'res_2160', 'type': 'checkbox', 'title': '4K', 'default': 'checked'},
        {'key': 'res_1080', 'type': 'checkbox', 'title': '1080p', 'default': 'checked'},
        {'key': 'res_720', 'type': 'checkbox', 'title': '720p', 'default': 'checked'},
        {'key': 'res_480', 'type': 'checkbox', 'title': '480p', 'default': 'checked'},
        {'key': 'res_360', 'type': 'checkbox', 'title': '360p', 'default': 'checked'},
        # Audio languages
        {'key': 'audio_hindi', 'type': 'checkbox', 'title': 'Audio: Hindi', 'default': 'checked'},
        {'key': 'audio_tamil', 'type': 'checkbox', 'title': 'Audio: Tamil', 'default': 'checked'},
        {'key': 'audio_telugu', 'type': 'checkbox', 'title': 'Audio: Telugu', 'default': 'checked'},
        {'key': 'audio_english', 'type': 'checkbox', 'title': 'Audio: English', 'default': 'checked'},
        {'key': 'audio_japanese', 'type': 'checkbox', 'title': 'Audio: Japanese', 'default': 'checked'},
        {'key': 'audio_malayalam', 'type': 'checkbox', 'title': 'Audio: Malayalam', 'default': 'unchecked'},
        {'key': 'audio_kannada', 'type': 'checkbox', 'title': 'Audio: Kannada', 'default': 'unchecked'},
        # Options
        {'key': 'subtitles_disabled', 'type': 'checkbox', 'title': 'Disable subtitles', 'default': 'unchecked'},
        {'key': 'hide_non_seekable', 'type': 'checkbox', 'title': 'Hide non-seekable streams', 'default': 'unchecked'},
    ],
    'behaviorHints': {'configurable': True, 'configurationRequired': False},
}


def make_manifest(config_segment=''):
    """Build manifest with config baked in"""
    m = dict(BASE_MANIFEST)
    if config_segment:
        m['id'] = f'com.multianima.{hash(config_segment) % 10000}'
    return m

MANIFEST = BASE_MANIFEST

@manifest_bp.route('/manifest.json')
@manifest_bp.route('/<lang>/manifest.json')
def addon_manifest(lang=None):
    return respond_with(BASE_MANIFEST, 7200)

@manifest_bp.route('/<config_data>/manifest.json')
def addon_manifest_config(config_data):
    config = parse_config(config_data)
    m = make_manifest(config_data)
    return respond_with(m, 7200)
