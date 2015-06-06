VERSION = '1.0.0'

def configure(**settings):
    from .settings import Settings
    for key, value in settings.items():
        Settings.setattr(key, value)
