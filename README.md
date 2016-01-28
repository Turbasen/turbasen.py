# turbasen.py

[![Build status](https://img.shields.io/wercker/ci/5572dde323929da36b16df5f.svg "Build status")](https://app.wercker.com/project/bykey/337a4c74baec7af88792f39c45715ff1)
[![PyPI downloads](https://img.shields.io/pypi/dm/turbasen.svg "PyPI downloads")](https://pypi.python.org/pypi/turbasen)
[![PyPi version](https://img.shields.io/pypi/v/turbasen.svg "PyPI version")](https://pypi.python.org/pypi/turbasen)
[![Python versions](https://img.shields.io/pypi/pyversions/turbasen.svg "Python versions")](https://pypi.python.org/pypi/turbasen)
[![Dependency status](https://img.shields.io/requires/github/Turbasen/turbasen.py.svg "Dependency status")](https://requires.io/github/Turbasen/turbasen.py/requirements/)

Python client for [Nasjonal Turbase](http://www.nasjonalturbase.no/)

## Usage

turbasen.py implements the following datatypes; import them from the `turbasen` module:

* `Gruppe`
* `Omrade`
* `Sted`

turbasen.py is opinionated about available data fields, see the `FIELDS` attribute on each data type in [the models](https://github.com/Turbasen/turbasen.py/blob/master/turbasen/models.py). Retrieving an object with unrecognized fields and saving it will delete those fields by default. Fields with value `None` are regarded as undefined.

### Static methods

`def lookup(pages=1, params={})`

Retrieve a list of all partial objects of this type. Limit the amount of objects returned by specifying `pages`. A page contains `settings.LIMIT` objects. Values in the `params` dict are passed as query parameters to the API.

`def get(object_id)`

Retrieve the entire document for the object with the given ID.

### Instance methods

`def save(include_extra=False)`

Save the object by performing a `POST` if the object is new (has no object id) or a `PUT` if it's an existing object. Existing data fields not recognized in our data model will be cleared on save (by not including them in the `PUT` request) unless you set `include_extra` to `True`.

`def get_data(self, include_common=True, include_extra=False)`

Returns a dict of all data fields on this object. Set `include_common` to `False` to only return fields specific to this datatype. Set `include_extra` to `True` to include fields not recognized in our data model.

## Example

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
* `CACHE_LOOKUP_PERIOD`: Number of seconds to retain a cached list.
* `CACHE_GET_PERIOD`: Number of seconds to retain a cached object. This should in most cases be very high, since their ETag will be checked regardless based on the `ETAG_CACHE_PERIOD` settings.
* `ETAG_CACHE_PERIOD`: Number of seconds to wait before verifying an object's ETag upon a `get` call and potentially refetch its document.

[See the source file for default values](https://github.com/Turbasen/turbasen.py/blob/master/turbasen/settings.py).

## Events

The client is able to trigger event handlers on a few occasions.

```python
import turbasen

def my_handler():
    pass

turbasen.handle_event('api.get_object', my_handler)
```

* `api.get_object`: GET request made for a single object
* `api.get_objects`: GET request for a new page with list of objects - called once for each new page
* `api.post_object`: POST request made with a new object
* `api.put_object`: PUT request made for an existing object
* `api.delete_object`: DELETE request made for an existing object
