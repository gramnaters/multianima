from flask import Blueprint, request
from .utils import respond_with
from app.config_parser import parse_config

manifest_bp = Blueprint('manifest', __name__)

BASE_MANIFEST = {
    'id': 'com.multianima.addon',
    'version': '1.0.0',
    'name': 'Multianima',
    'description': 'Multi-provider anime: 20 players across 5 sites. AnVod, Pahe, GDMirror, VMoly, StreamRuby, DoodStream, StreamTape, StreamP2P, RPMShare, UPNShare, ZephyrFlick, TurboVid, VidSrc, VidRocks, Abyss, FlixCloud + more',
    'types': ['anime', 'series', 'movie'],
    'idPrefixes': ['tt', 'hd'],
    'catalogs': [
        {'type': 'anime', 'id': 'hd_all', 'name': 'Hindi Dub Anime', 'extra': [
            {'name': 'search', 'isRequired': True}, {'name': 'skip', 'isRequired': False},
        ]},
        {'type': 'anime', 'id': 'hd_latest', 'name': 'Latest Releases'},
    ],
    'behaviorHints': {'configurable': True, 'configurationRequired': False},
    'resources': ['catalog', 'meta', 'stream'],
}

def make_manifest(config_segment=''):
    """Build manifest with encoded config baked into URLs"""
    m = dict(BASE_MANIFEST)
    m['id'] = f'com.multianima.{hash(config_segment) % 10000}'
    return m

MANIFEST = BASE_MANIFEST  # alias for run.py import

@manifest_bp.route('/manifest.json')
@manifest_bp.route('/<lang>/manifest.json')
def addon_manifest(lang=None):
    return respond_with(BASE_MANIFEST, 7200)

@manifest_bp.route('/<config_data>/manifest.json')
def addon_manifest_config(config_data):
    config = parse_config(config_data)
    m = make_manifest(config_data)
    return respond_with(m, 7200)
