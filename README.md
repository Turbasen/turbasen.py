# turbasen.py
Python client for Nasjonal Turbase

## Usage

```python
In [1]: from turbasen import Sted, Omrade

In [2]: Sted.get('52407fb375049e561500004e')
Out[2]: Sted: 52407fb375049e561500004e (Tjørnbrotbu)

In [3]: for sted in list(Sted.lookup())[:3]:
            print(sted)

Sted: 52407fb375049e5615000356 (Lahpoluoppal)
Sted: 52407fb375049e561500027d (Øvre Grue)
Sted: 52407fb375049e5615000385 (Rotneros)

In [4]: for omrade in list(Omrade.lookup())[:3]:
            print(omrade)

Område: 52408144e7926dcf15000004 (Sørlandet)
Område: 52408144e7926dcf1500002b (Østlandet)
Område: 52408144e7926dcf1500000e (Vestlandet)
```


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
