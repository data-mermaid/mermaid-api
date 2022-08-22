
# Source: https://github.com/ianlini/flatten-dict
import os.path
from collections.abc import Mapping
import six


def tuple_reducer(k1, k2):
    if k1 is None:
        return (k2,)
    else:
        return k1 + (k2,)


def path_reducer(k1, k2):
    if k1 is None:
        return k2
    else:
        return os.path.join(k1, k2)


def dot_reducer(k1, k2):
    if k1 is None:
        return k2
    else:
        return '{}.{}'.format(k1, k2)


REDUCER_DICT = {
    'tuple': tuple_reducer,
    'path': path_reducer,
    'dot': dot_reducer,
}


def flatten(d, reducer='dot', inverse=False):
    """Flatten dict-like object.

    Parameters
    ----------
    d: dict-like object
        The dict that will be flattened.
    reducer: {'tuple', 'path', function} (default: 'tuple')
        The key joining method. If a function is given, the function will be
        used to reduce.
        'tuple': The resulting key will be tuple of the original keys
        'path': Use ``os.path.join`` to join keys.
    inverse: bool (default: False)
        Whether you want invert the resulting key and value.

    Returns
    -------
    flat_dict: dict
    """
    if isinstance(reducer, str):
        reducer = REDUCER_DICT[reducer]
    flat_dict = {}

    def _flatten(d, parent=None):
        for key, val in six.viewitems(d):
            flat_key = reducer(parent, key)
            if isinstance(val, Mapping):
                _flatten(val, flat_key)
            elif inverse:
                if val in flat_dict:
                    raise ValueError("duplicated key '{}'".format(val))
                flat_dict[val] = flat_key
            else:
                flat_dict[flat_key] = val

    _flatten(d)
    return flat_dict
