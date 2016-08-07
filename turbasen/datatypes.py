from .apiclient import NTBObject

class Bilde(NTBObject):
    identifier = 'bilder'

class Gruppe(NTBObject):
    identifier = 'grupper'

class Område(NTBObject):
    identifier = 'områder'

class Sted(NTBObject):
    identifier = 'steder'

class Tur(NTBObject):
    identifier = 'turer'
