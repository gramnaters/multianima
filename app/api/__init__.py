# Providers: scraper classes for each anime site
from app.api.animelok import AnimeLokAPI
from app.api.watchanimeworld import WatchAnimeWorldAPI
from app.api.desidubanime import DesiDubAnimeAPI
from app.api.animesalt import AnimeSaltAPI
from app.api.animejoker import AnimeJokerAPI
from app.api.bashapi import BashAPIProvider
from app.api.animevilla import AnimeVillaProvider

animelok = AnimeLokAPI()
watchanimeworld = WatchAnimeWorldAPI()
desidubanime = DesiDubAnimeAPI()
animesalt = AnimeSaltAPI()
animejoker = AnimeJokerAPI()
bashapi = BashAPIProvider()
animevilla = AnimeVillaProvider()

ALL_PROVIDERS = {
    'animelok': animelok,
    'watchanimeworld': watchanimeworld,
    'desidubanime': desidubanime,
    'animesalt': animesalt,
    'animejoker': animejoker,
    'bashapi': bashapi,
    'animevilla': animevilla,
}
