# coding: utf8
from __future__ import unicode_literals, print_function, division


def test_cache(tmppath):
    from pylexibank.cache import Cache

    cache = Cache(tmppath)
    cache['key'] = 5
    assert cache.get('key', 10) == 5
    assert cache.get('xy', 10) == 10
    del cache['key']
    assert list(cache.keys()) == ['xy']
    cache.clear()
    assert len(cache) == 0
