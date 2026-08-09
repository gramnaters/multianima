"""
Config parsing utilities - shared between routes and run.py without circular imports.
"""
import base64
import json
import urllib.parse


def parse_config(segment: str) -> dict:
    """Parse config from URL path segment. Supports base64url + JSON."""
    if not segment:
        return _default_config()
    try:
        decoded = urllib.parse.unquote(segment)
        padded = decoded + '=' * (4 - len(decoded) % 4)
        try:
            raw = base64.urlsafe_b64decode(padded)
            return json.loads(raw)
        except:
            pass
        return json.loads(decoded)
    except:
        return _default_config()


def _default_config():
    return {
        'source_animelok': 'on',
        'source_watchanimeworld': 'on',
        'source_animesalt': 'on',
        'source_animejoker': 'on',
        'source_desidubanime': 'on',
        'source_bashapi': 'off',
        'res_2160': 'on', 'res_1080': 'on', 'res_720': 'on', 'res_480': 'on', 'res_360': 'on',
        'audio_hindi': 'on', 'audio_tamil': 'on', 'audio_telugu': 'on',
        'audio_english': 'on', 'audio_japanese': 'on',
        'audio_malayalam': 'off', 'audio_kannada': 'off',
        'subtitles_disabled': 'off', 'hide_non_seekable': 'off',
    }


def get_provider_from_config(config: dict) -> list:
    """Get enabled providers from config"""
    providers = []
    for k, v in config.items():
        if k.startswith('source_') and v == 'on':
            providers.append(k.replace('source_', ''))
    return providers


def get_players_from_config(config: dict) -> list:
    """Get enabled players from config"""
    players = []
    for k, v in config.items():
        if k.startswith('plr_') and v == 'on':
            players.append(k.replace('plr_', ''))
    return players


def get_langs_from_config(config: dict) -> list:
    """Get enabled audio languages from config"""
    langs = []
    for k, v in config.items():
        if k.startswith('audio_') and v == 'on':
            langs.append(k.replace('audio_', ''))
    return langs


def get_quality_from_config(config: dict) -> list:
    """Get enabled quality levels from config"""
    qualities = []
    for k, v in config.items():
        if k.startswith('res_') and v == 'on':
            try:
                qualities.append(int(k.replace('res_', '')))
            except:
                pass
    return sorted(qualities, reverse=True)


def is_hide_non_seekable(config: dict) -> bool:
    return config.get('hide_non_seekable') == 'on'


def is_subtitles_disabled(config: dict) -> bool:
    return config.get('subtitles_disabled') == 'on'


def encode_config(config: dict) -> str:
    """Encode config dict to base64url string for URL embedding"""
    json_str = json.dumps(config, separators=(',', ':'))
    return base64.urlsafe_b64encode(json_str.encode()).decode().rstrip('=')
