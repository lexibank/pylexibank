from pyglottolog import api
from clldutils.misc import lazyproperty

from pylexibank.util import Repos


class Glottolog(api.Glottolog, Repos):
    @lazyproperty
    def cached_languoids(self):
        return {l.id: l for l in self.languoids()}

    @lazyproperty
    def languoid_details(self):
        return {
            lid: (l.iso, l.macroareas, l.name) for lid, l in self.cached_languoids.items()
        }

    @lazyproperty
    def glottocode_by_name(self):
        return {l[2]: lid for lid, l in self.languoid_details.items()}

    @lazyproperty
    def glottocode_by_iso(self):
        return {l[0]: lid for lid, l in self.languoid_details.items() if l[0]}

    @lazyproperty
    def macroareas_by_glottocode(self):
        return {lid: l[1] for lid, l in self.languoid_details.items()}
