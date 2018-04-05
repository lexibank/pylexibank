# coding: utf8
from __future__ import unicode_literals, print_function, division
from importlib import import_module

from clldutils.path import Path

for p in Path(__file__).parent.iterdir():
    if (p.is_file() and p.stem != '__init__' and p.name[0] != '.') \
            or (p.is_dir() and p.joinpath('__init__.py').exists()):
        import_module('{0}.{1}'.format(__name__, p.stem))
