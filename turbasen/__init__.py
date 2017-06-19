# Import the models we want directly available through the root module
from .datatypes import ( # noqa
    Bilde,
    Gruppe,
    Liste,
    Område,
    Sted,
    Tur,
)

# Make configure directly available through the root module
from .settings import configure # noqa

# Make handle_event available directly available through the root module
from .events import handle_event # noqa
