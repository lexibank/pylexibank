import re
import collections
import pkg_resources

import attr
from cldfbench.metadata import Metadata

__all__ = ['LexibankMetadata', 'check_standard_title', 'iter_contributors']

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
    import os, pytest

    @pytest.mark.skipif("TRAVIS" in os.environ and os.environ["TRAVIS"] == "true")
    def test_valid_title(cldf_dataset, cldf_logger):
        from pylexibank import check_standard_title
        check_standard_title(cldf_dataset.metadata_dict['dc:title'])
    ```
    """
    match = STANDARD_TITLE_PATTERN.fullmatch(title)
    assert match and match.group('authors').strip().endswith(("'s", "s'"))


def iter_contributors(fname_or_lines):
    header, in_table = None, False

    def row(line):
        return [l.strip() for l in line.split('|')]

    for line in (fname_or_lines if isinstance(fname_or_lines, list) else fname_or_lines.open()):
        if in_table:
            if '|' not in line:  # Last row of table was already read
                break
            yield collections.OrderedDict(zip(header, row(line)))
        elif '|' in line:
            r = row(line)
            if not ''.join(r).replace('-', ''):  # a line like " --- | --- | --- "
                assert header
                in_table = True
            else:
                header = r


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
