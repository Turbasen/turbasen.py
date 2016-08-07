from .apiclient import NTBObject

class Bilde(NTBObject):
    identifier = 'bilder'
    FIELDS = [
        'geojson',
        'beskrivelse',
        'fotograf',
        'eier',
        'tags',
        'grupper',
        'img',
    ]

class Gruppe(NTBObject):
    identifier = 'grupper'
    FIELDS = [
        'geojson',
        'områder',
        'kommuner',
        'fylker',
        'organisasjonsnr',
        'beskrivelse',
        'logo',
        'ansatte',
        'lenker',
        'kontaktinfo',
        'tags',
        'foreldregruppe',
        'privat',
        'grupper',
        'bilder',
        'steder',
        'url',
    ]

class Omrade(NTBObject):
    identifier = 'områder'
    FIELDS = [
        'geojson',
        'kommuner',
        'fylker',
        'beskrivelse',
        'bilder',
    ]

class Sted(NTBObject):
    identifier = 'steder'
    FIELDS = [
        'navn_alt',
        'ssr_id',
        'geojson',
        'områder',
        'kommune',
        'fylke',
        'beskrivelse',
        'adkomst',
        'tilrettelagt_for',
        'fasiliteter',
        'lenker',
        'byggeår',
        'besøksstatistikk',
        'betjeningsgrad',
        'tags',
        'grupper',
        'bilder',
        'steder',
        'url',
        'kart',
        'turkart',
    ]

class Tur(NTBObject):
    identifier = 'turer'
    FIELDS = [
        'geojson',
        'distanse',
        'retning',
        'områder',
        'fylker',
        'beskrivelse',
        'adkomst',
        'lenker',
        'gradering',
        'passer_for',
        'tilrettelagt_for',
        'sesong',
        'tidsbruk',
        'tags',
        'grupper',
        'bilder',
        'steder',
        'url',
    ]
