# turbasen.py
Python client for Nasjonal Turbase

## Configuration

Call `turbasen.configure` to change settings. For example:

```python
import turbasen
turbasen.configure(
    LIMIT=50,
    CACHE=my_cache,
)
```

[The available settings](https://github.com/Turbasen/turbasen.py/blob/master/turbasen/settings.py) are:

* `ENDPOINT_URL`: The URL to the Nasjonal Turbase API endpoint
* `LIMIT`: Results per page when fetching multiple objects. Currently allows up to 50; [see the docs](http://www.nasjonalturbase.no/) for updates.
* `CACHE`: If specified, the library will itself perform what it deems to be reasonable caching of lookups and objects. Expects a cache engine implementing a small subset of [the Django cache API](https://docs.djangoproject.com/en/dev/topics/cache/#the-low-level-cache-api), specifically its `get` and `set` methods.
* `API_KEY`: Currently an API key is required for access, however there are plans to drop the key requirement. [See the website](http://www.nasjonalturbase.no/) for updates. The API key can also be specified as an exported environment variable called `TURBASEN_API_KEY`.

[See the source file for default values](https://github.com/Turbasen/turbasen.py/blob/master/turbasen/settings.py).
