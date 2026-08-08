# Providers: scraper classes for each anime site
from app.api.animelok import AnimeLokAPI
from app.api.watchanimeworld import WatchAnimeWorldAPI
from app.api.desidubanime import DesiDubAnimeAPI
from app.api.animesalt import AnimeSaltAPI
from app.api.animejoker import AnimeJokerAPI

animelok = AnimeLokAPI()
watchanimeworld = WatchAnimeWorldAPI()
desidubanime = DesiDubAnimeAPI()
animesalt = AnimeSaltAPI()
animejoker = AnimeJokerAPI()

ALL_PROVIDERS = {
    'animelok': animelok,
    'watchanimeworld': watchanimeworld,
    'desidubanime': desidubanime,
    'animesalt': animesalt,
    'animejoker': animejoker,
}
