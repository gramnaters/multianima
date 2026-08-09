# Providers: scraper classes for each anime site
# Old providers (scraping-based)
from app.api.animelok import AnimeLokAPI
from app.api.watchanimeworld import WatchAnimeWorldAPI
from app.api.desidubanime import DesiDubAnimeAPI
from app.api.animesalt import AnimeSaltAPI
from app.api.animejoker import AnimeJokerAPI
from app.api.bashapi import BashAPIProvider
from app.api.animevilla import AnimeVillaProvider
from app.api.aniflix import AniflixProvider

# New reverse-engineered providers (API-based)
from app.api.newproviders.direct import ALL_NEW_PROVIDERS as DIRECT_PROVIDERS
from app.api.newproviders import ALL_NEW_PROVIDERS as INIT_PROVIDERS

# Merge both
ALL_NEW_PROVIDERS = {**DIRECT_PROVIDERS, **INIT_PROVIDERS}

animelok = AnimeLokAPI()
watchanimeworld = WatchAnimeWorldAPI()
desidubanime = DesiDubAnimeAPI()
animesalt = AnimeSaltAPI()
animejoker = AnimeJokerAPI()
bashapi = BashAPIProvider()
animevilla = AnimeVillaProvider()
aniflix = AniflixProvider()

ALL_PROVIDERS = {
    'animelok': animelok,
    'watchanimeworld': watchanimeworld,
    'desidubanime': desidubanime,
    'animesalt': animesalt,
    'animejoker': animejoker,
    'bashapi': bashapi,
    'animevilla': animevilla,
    'aniflix': aniflix,
}

# Merge new providers
ALL_PROVIDERS.update(ALL_NEW_PROVIDERS)
