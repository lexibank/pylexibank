# coding: utf8
from __future__ import unicode_literals, print_function, division

from pyconcepticon import api

from pylexibank.util import Repos


class Concepticon(api.Concepticon, Repos):
    pass
