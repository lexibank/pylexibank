# coding: utf8
from __future__ import unicode_literals, print_function, division

from pyglottolog import api
from clldutils.misc import cached_property

from pylexibank.cache import Cache
from pylexibank.util import Repos


class Glottolog(api.Glottolog, Repos):
    @cached_property()
    def languoid_details(self):
        def _get():
            return {l.id: (l.iso, l.macroareas, l.name) for l in self.languoids()}
        return Cache().get('glottolog', _get)

    @cached_property()
    def glottocode_by_name(self):
        return {l[2]: lid for lid, l in self.languoid_details.items()}

    @cached_property()
    def glottocode_by_iso(self):
        return {l[0]: lid for lid, l in self.languoid_details.items() if l[0]}

    @cached_property()
    def macroareas_by_glottocode(self):
        def _get():
            return {lid: l[1] for lid, l in self.languoid_details.items()}
        return Cache().get('macroareas', _get)
