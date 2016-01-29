def params_to_dotnotation(params, path=''):
    """
    Transforms a dict of dicts to query parameters with dotted path as accpted by Turbasen, ex:
    {
        'foo': 'bar',
        'bar': {
            'baz': {
                'abc': 42,
                'def': 43,
                'foo': {
                    'wat': '',
                },
            },
            'ghi': 44,
        },
        'jkl': 'mno',
    }

    {
        'foo': 'bar',
        'bar.baz.abc': 42,
        'bar.baz.def': 43,
        'bar.baz.foo.wat': '',
        'bar.ghi': 44,
        'jkl': 'mno',
    }
    """
    dotted_dict = {}
    for key, value in params.items():
        full_path = key if path == '' else '%s.%s' % (path, key)
        if type(value) != dict:
            dotted_dict[full_path] = value
        else:
            dotted_dict.update(params_to_dotnotation(value, path=full_path))
    return dotted_dict
