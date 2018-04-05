# *-* coding: utf-8 *-*
"""Implements the lexibank cache. (copied from lingpy3)
"""
from __future__ import unicode_literals, print_function, absolute_import, division
import logging

import dill
from clldutils.path import Path, path_component, remove, as_unicode
from appdirs import user_cache_dir


PKG_NAME = __name__.split('.')[0]
CACHE_DIR = user_cache_dir(PKG_NAME)


class Cache(object):
    def __init__(self, dir_=None):
        self._dir = Path(dir_ or CACHE_DIR)
        if not self._dir.exists():
            self._dir.mkdir(parents=True)  # pragma: no cover
        self.log = logging.getLogger(PKG_NAME)

    def _path(self, key):
        return self._dir.joinpath(path_component(key))

    def __len__(self):
        return len(list(self.keys()))

    def get(self, item, default):
        if item in self:
            return self[item]
        res = self[item] = default() if callable(default) else default
        return res

    def __getitem__(self, item):
        self.log.debug('cache hit: {0}'.format(item))
        with self._path(item).open('rb') as fp:
            return dill.load(fp)

    def __setitem__(self, key, value):
        self.log.debug('cache miss: {0}'.format(key))
        with self._path(key).open('wb') as fp:
            dill.dump(value, fp)

    def __delitem__(self, key):
        remove(self._path(key))

    def __contains__(self, item):
        return self._path(item).exists()

    def keys(self):
        for p in self._dir.iterdir():
            yield as_unicode(p.name)

    def clear(self):
        for key in self.keys():
            remove(self._path(key))
