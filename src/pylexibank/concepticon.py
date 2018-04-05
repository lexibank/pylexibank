# coding: utf8
from __future__ import unicode_literals, print_function, division

from pyconcepticon import api
from clldutils.misc import cached_property

from pylexibank.cache import Cache
from pylexibank.util import Repos


class Concepticon(api.Concepticon, Repos):
    pass
