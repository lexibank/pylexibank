import re
import collections
import pkg_resources

import attr
from clldutils.misc import nfilter
from cldfbench.metadata import Metadata

__all__ = ['LexibankMetadata', 'check_standard_title', 'get_creators_and_contributors']

version = pkg_resources.get_distribution('pylexibank').version

STANDARD_TITLE_PATTERN = re.compile(
    r'CLDF dataset derived from\s+'
    r'(?P<authors>[^"]+)'
    r'"(?P<title>[^"]+)"\s+from\s+'
    r'(?P<year>[0-9]{4})'
)
CONTRIBUTOR_TYPES = {
    'ContactPerson',
    'DataCollector',
    'DataCurator',
    'DataManager',
    'Distributor',
    'Editor',
    'Funder',
    'HostingInstitution',
    'Producer',
    'ProjectLeader',
    'ProjectManager',
    'ProjectMember',
    'RegistrationAgency',
    'RegistrationAuthority',
    'RelatedPerson',
    'Researcher',
    'ResearchGroup',
    'RightsHolder',
    'Supervisor',
    'Sponsor',
    'WorkPackageLeader',
    'Other',
}
LICENSES = {
    "AAL",
    "ADSL",
    "AFL-1.1",
    "AFL-3.0",
    "AGPL-1.0-only",
    "AGPL-3.0",
    "AGPL-3.0-only",
    "AGPL-3.0-or-later",
    "AMDPLPA",
    "AML",
    "AMPAS",
    "ANTLR-PD",
    "APL-1.0",
    "APSL-1.0",
    "APSL-1.1",
    "APSL-1.2",
    "APSL-2.0",
    "Adobe-2006",
    "Against-DRM",
    "Aladdin",
    "Apache-1.0",
    "Apache-1.1",
    "Apache-2.0",
    "Artistic-1.0",
    "Artistic-1.0-Perl",
    "Artistic-1.0-cl8",
    "Artistic-2.0",
    "BSD-1-Clause",
    "BSD-2-Clause",
    "BSD-2-Clause-FreeBSD",
    "BSD-3-Clause",
    "BSD-3-Clause-Clear",
    "BSD-3-Clause-LBNL",
    "BSD-3-Clause-No-Nuclear-License",
    "BSD-3-Clause-No-Nuclear-License-2014",
    "BSD-4-Clause",
    "BSD-4-Clause-UC",
    "BSD-Source-Code",
    "BSL-1.0",
    "Bahyph",
    "Barr",
    "Beerware",
    "BitTorrent-1.0",
    "BitTorrent-1.1",
    "CATOSL-1.1",
    "CC-BY-1.0",
    "CC-BY-3.0",
    "CC-BY-4.0",
    "CC-BY-NC-1.0",
    "CC-BY-NC-2.5",
    "CC-BY-NC-3.0",
    "CC-BY-NC-4.0",
    "CC-BY-NC-ND-1.0",
    "CC-BY-NC-ND-2.0",
    "CC-BY-NC-ND-2.5",
    "CC-BY-NC-ND-3.0",
    "CC-BY-NC-ND-4.0",
    "CC-BY-NC-SA-1.0",
    "CC-BY-NC-SA-3.0",
    "CC-BY-NC-SA-4.0",
    "CC-BY-ND-1.0",
    "CC-BY-ND-2.0",
    "CC-BY-ND-2.5",
    "CC-BY-ND-4.0",
    "CC-BY-SA-2.0",
    "CC-BY-SA-2.5",
    "CC-BY-SA-3.0",
    "CC-BY-SA-4.0",
    "CC0-1.0",
    "CDDL-1.0",
    "CDLA-Permissive-1.0",
    "CDLA-Sharing-1.0",
    "CECILL-1.1",
    "CECILL-2.0",
    "CECILL-2.1",
    "CECILL-B",
    "CECILL-C",
    "CNRI-Jython",
    "CNRI-Python",
    "CNRI-Python-GPL-Compatible",
    "CPAL-1.0",
    "CPOL-1.02",
    "CUA-OPL-1.0",
    "Caldera",
    "ClArtistic",
    "Condor-1.1",
    "CrystalStacker",
    "Cube",
    "D-FSL-1.0",
    "DSDP",
    "DSL",
    "ECL-2.0",
    "EFL-1.0",
    "EFL-2.0",
    "EPL-1.0",
    "EUDatagrid",
    "EUPL-1.0",
    "EUPL-1.1",
    "EUPL-1.2",
    "Entessa",
    "ErlPL-1.1",
    "Eurosym",
    "FAL-1.3",
    "FSFAP",
    "Fair",
    "Frameworx-1.0",
    "GFDL-1.1",
    "GFDL-1.1-only",
    "GFDL-1.2",
    "GFDL-1.2-only",
    "GFDL-1.2-or-later",
    "GFDL-1.3-no-cover-texts-no-invariant-sections",
    "GL2PS",
    "GPL-1.0+",
    "GPL-1.0-or-later",
    "GPL-2.0",
    "GPL-2.0+",
    "GPL-2.0-with-GCC-exception",
    "GPL-2.0-with-bison-exception",
    "GPL-2.0-with-classpath-exception",
    "GPL-3.0",
    "GPL-3.0-only",
    "GPL-3.0-or-later",
    "GPL-3.0-with-GCC-exception",
    "Giftware",
    "Glulxe",
    "HPND",
    "HaskellReport",
    "IBM-pibs",
    "ICU",
    "IJG",
    "IPA",
    "IPL-1.0",
    "ISC",
    "ImageMagick",
    "Imlib2",
    "Intel",
    "Intel-ACPI",
    "JSON",
    "LGPL-2.0",
    "LGPL-2.0-or-later",
    "LGPL-2.1",
    "LGPL-2.1-only",
    "LGPL-3.0",
    "LGPL-3.0-or-later",
    "LGPLLR",
    "LPL-1.0",
    "LPL-1.02",
    "LPPL-1.0",
    "LPPL-1.2",
    "LPPL-1.3c",
    "LiLiQ-R-1.1",
    "LiLiQ-Rplus-1.1",
    "Linux-OpenIB",
    "MIT",
    "MIT-advertising",
    "MIT-enna",
    "MPL-1.0",
    "MPL-1.1",
    "MPL-2.0",
    "MPL-2.0-no-copyleft-exception",
    "MS-PL",
    "MS-RL",
    "MirOS",
    "Motosoto",
    "Multics",
    "Mup",
    "NASA-1.3",
    "NCSA",
    "NGPL",
    "NOSL",
    "NPL-1.1",
    "NPOSL-3.0",
    "NTP",
    "Naumen",
    "Newsletr",
    "Nokia",
    "Noweb",
    "Nunit",
    "OCCT-PL",
    "OCLC-2.0",
    "ODC-By-1.0",
    "ODC-PDDL-1.0",
    "ODbL-1.0",
    "OFL-1.0",
    "OFL-1.1",
    "OGL-Canada-2.0",
    "OGL-UK-1.0",
    "OGL-UK-2.0",
    "OGL-UK-3.0",
    "OGTSL",
    "OLDAP-1.2",
    "OLDAP-1.3",
    "OLDAP-1.4",
    "OLDAP-2.0",
    "OLDAP-2.0.1",
    "OLDAP-2.1",
    "OLDAP-2.2",
    "OLDAP-2.2.1",
    "OLDAP-2.2.2",
    "OLDAP-2.3",
    "OLDAP-2.4",
    "OLDAP-2.6",
    "OLDAP-2.8",
    "OSET-PL-2.1",
    "OSL-1.0",
    "OSL-1.1",
    "OSL-2.0",
    "OSL-2.1",
    "OSL-3.0",
    "OpenSSL",
    "PHP-3.0",
    "PHP-3.01",
    "Plexus",
    "PostgreSQL",
    "Python-2.0",
    "QPL-1.0",
    "Qhull",
    "RHeCos-1.1",
    "RPL-1.1",
    "RPL-1.5",
    "RPSL-1.0",
    "RSA-MD",
    "RSCPL",
    "Ruby",
    "SAX-PD",
    "SCEA",
    "SGI-B-2.0",
    "SISSL",
    "SMLNJ",
    "SPL-1.0",
    "SWL",
    "Sendmail",
    "Sendmail-8.23",
    "SimPL-2.0",
    "Sleepycat",
    "Spencer-94",
    "Spencer-99",
    "SugarCRM-1.1.3",
    "TCL",
    "TCP-wrappers",
    "TOSL",
    "TU-Berlin-2.0",
    "Unicode-DFS-2015",
    "Unicode-TOU",
    "Unlicense",
    "VSL-1.0",
    "Vim",
    "W3C",
    "W3C-20150513",
    "Watcom-1.0",
    "X11",
    "XFree86-1.1",
    "XSkat",
    "Xerox",
    "Xnet",
    "ZPL-1.1",
    "ZPL-2.0",
    "Zed",
    "Zend-2.0",
    "Zimbra-1.3",
    "Zlib",
    "bsd-license",
    "bzip2-1.0.5",
    "canada-crown",
    "cc-nc",
    "curl",
    "diffmark",
    "dli-model-use",
    "dvipdfm",
    "eCos-2.0",
    "eGenix",
    "eurofound",
    "geo-no-fee-unrestricted",
    "geogratis",
    "gnuplot",
    "hesa-withrights",
    "jabber-osl",
    "libtiff",
    "localauth-withrights",
    "lucent-plan9",
    "met-office-cp",
    "mitre",
    "mpich2",
    "notspecified",
    "other-at",
    "other-closed",
    "other-nc",
    "other-open",
    "other-pd",
    "psfrag",
    "psutils",
    "ukclickusepsi",
    "ukcrown",
    "ukcrown-withrights",
    "ukpsi",
    "user-jsim",
    "wxWindows",
    "xpp",
    "zlib-acknowledgement",
}


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


def get_creators_and_contributors(fname, strict=True):
    ctypes = {c.lower(): c for c in CONTRIBUTOR_TYPES}
    creators, contributors = [], []
    for row in iter_rows(fname):
        row = {k.lower(): v for k, v in row.items()}
        for role in nfilter([r.strip().lower() for r in row.get('role', '').split(',')]):
            c = {k: v for k, v in row.items() if k != 'role'}
            if role in {'author', 'creator', 'maintainer'}:
                creators.append(c)
            else:
                if strict:
                    c['type'] = ctypes[role]
                else:
                    c['type'] = ctypes.get(role, 'Other')
                contributors.append(c)
    return creators, contributors


def iter_rows(fname_or_lines):
    header, in_table = None, False

    def row(line):
        return [li.strip() for li in line.split('|')]

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

    @property
    def zenodo_license(self):
        if self.known_license and self.known_license.id in LICENSES:
            return self.known_license.id

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
