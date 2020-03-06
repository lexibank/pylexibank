import pkg_resources

import attr
from cldfbench.metadata import Metadata

__all__ = ['LexibankMetadata']

version = pkg_resources.get_distribution('pylexibank').version


@attr.s
class LexibankMetadata(Metadata):
    aboutUrl = attr.ib(default=None)
    conceptlist = attr.ib(
        default=[],
        converter=lambda s: [] if not s else (s if isinstance(s, list) else [s]))
    lingpy_schema = attr.ib(default=None)
    derived_from = attr.ib(default=None)
    related = attr.ib(default=None)
    source = attr.ib(default=None)
    patron = attr.ib(default=None)
    version = attr.ib(default=version)

    def common_props(self):
        res = super().common_props()
        res.update({
            "dc:format": [
                "http://concepticon.clld.org/contributions/{0}".format(cl)
                for cl in self.conceptlist],
            "dc:isVersionOf": "http://lexibank.clld.org/contributions/{0}".format(
                self.derived_from) if self.derived_from else None,
            "dc:related": self.related,
            "aboutUrl": self.aboutUrl
        })
        return res

    def markdown(self):
        lines = [super().markdown(), '']

        if self.related:
            lines.append('See also %s\n' % self.related)

        if self.conceptlist:
            lines.append('Conceptlists in Concepticon:')
            lines.extend([
                '- [{0}](https://concepticon.clld.org/contributions/{0})'.format(cl)
                for cl in self.conceptlist])
            lines.append('')
        return '\n'.join(lines)
