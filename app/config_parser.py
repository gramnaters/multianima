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
        'src_animelok': 'on', 'src_watchanimeworld': 'on', 'src_animesalt': 'on',
        'src_animejoker': 'on', 'src_desidubanime': 'on',
        'l_hindi': 'on', 'l_tamil': 'on', 'l_telugu': 'on',
        'l_english': 'on', 'l_japanese': 'on',
        'q_1080': 'on', 'q_720': 'on', 'q_480': 'on',
        'plr_gdmirrorbot': 'on', 'plr_vidmoly': 'on', 'plr_streamruby': 'on',
        'plr_doodstream': 'on', 'plr_streamtape': 'on', 'plr_turbovid': 'on',
        'plr_streamp2p': 'on', 'plr_rpmstream': 'on', 'plr_upnshare': 'on',
        'plr_vidsrc': 'on', 'plr_zephyrflick': 'on', 'plr_streamhg': 'on',
        'plr_vidrocks': 'on', 'plr_abyss': 'on', 'plr_flixcloud': 'on',
        'plr_moviesapi': 'on', 'plr_videasy': 'on', 'plr_playmogo': 'on',
        'subs': 'on', 'proxy': 'off', 'timeout': '15', 'max': '15',
    }


def get_provider_from_config(config: dict) -> list:
    return [k.replace('src_', '') for k in config if k.startswith('src_') and config[k] == 'on']


def get_players_from_config(config: dict) -> list:
    return [k.replace('plr_', '') for k in config if k.startswith('plr_') and config[k] == 'on']


def get_langs_from_config(config: dict) -> list:
    return [k.replace('l_', '') for k in config if k.startswith('l_') and config[k] == 'on']


def encode_config(config: dict) -> str:
    """Encode config dict to base64url string for URL embedding"""
    json_str = json.dumps(config, separators=(',', ':'))
    return base64.urlsafe_b64encode(json_str.encode()).decode().rstrip('=')
