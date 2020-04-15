import re
import pkg_resources

import attr
from cldfbench.metadata import Metadata

__all__ = ['LexibankMetadata', 'check_standard_title']

version = pkg_resources.get_distribution('pylexibank').version

STANDARD_TITLE_PATTERN = re.compile(
    r'CLDF dataset derived from\s+'
    r'(?P<authors>[^"]+)'
    r'"(?P<title>[^"]+)"\s+from\s+'
    r'(?P<year>[0-9]{4})'
)


def check_standard_title(title):
    """
    Assert a title conforms to the standard format.

    > CLDF dataset derived from AUTHOR's "TITLE" from YEAR

    Usage: In a dataset's `test.py`:
    ```python
    from pylexibank import check_standard_title

    def test_valid_title(cldf_dataset, cldf_logger):
        check_standard_title(cldf_dataset.metadata_dict['dc:title'])
    ```

    Note that this requires installing `pylexibank` for tests, also in .travis.yml.
    """
    match = STANDARD_TITLE_PATTERN.fullmatch(title)
    assert match and match.group('authors').strip().endswith("'s")


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
