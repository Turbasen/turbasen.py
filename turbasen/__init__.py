# Import the models we want directly available through the root module
from .models import (
    Bilde,
    Gruppe,
    Omrade,
    Sted,
    Tur,
)

# Make configure directly available through the root module
from .settings import configure

# Make handle_available directly available through the root module
from .events import handle_event
