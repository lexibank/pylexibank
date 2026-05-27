"""
Functionality to convert BVD-style data to Lexibank Wordlists.
"""
import re
import logging
import pathlib
import argparse
import dataclasses
from typing import Optional, Any
from collections.abc import Generator, Iterable
from xml.etree import ElementTree as et

from clldutils.misc import slug, nfilter
from pycldf.sources import Source
from simplepybtex.database import parse_string
from pylexibank import Dataset, Language as BaseLanguage

BASE_URL = "https://abvd.eva.mpg.de"
URL = BASE_URL + "/utils/save/?type=xml&section=%s&language=%d"


@dataclasses.dataclass
class BVDLanguage(BaseLanguage):
    """BVD languages have some editorial metadata."""
    author: Optional[str] = None
    url: Optional[str] = None
    typedby: Optional[str] = None
    checkedby: Optional[str] = None
    notes: Optional[str] = None
    source: Optional[str] = None


class BVD(Dataset):
    """BVD-specific Dataset implementation, reads data from XML."""
    SECTION = None
    invalid_ids = []
    language_ids = list(range(1, 50))  # list of language ids to look for.
    language_class = BVDLanguage
    cognate_pattern = re.compile(r'''\s*(?P<id>([A-z]?[0-9]+|[A-Z]))\s*(?P<doubt>\?+)?\s*$''')

    def iter_wordlists(self, log=None) -> Generator['Wordlist', None, None]:
        """Yield Wordlists initialized from XML files in raw dir."""
        for xml in sorted(self.raw_dir.glob('*.xml'), key=lambda p: int(p.stem)):
            yield Wordlist(self, xml, log)

    def cmd_download(self, args: argparse.Namespace):  # pragma: no cover
        """Download BVD XML wordlists form the app."""
        assert self.SECTION in ['austronesian', 'mayan', 'utoaztecan']
        args.log.info('ABVD section set to %s', self.SECTION)
        # remove
        for fname in self.raw_dir.iterdir():
            fname.unlink()

        for lid in self.language_ids:
            if lid in self.invalid_ids:
                args.log.warning("Skipping %s %d - invalid ID", self.SECTION, lid)
                continue

            if not self.get_data(lid):
                args.log.warning("No content for %s %d. Ending.", self.SECTION, lid)
                break

            args.log.info("Downloaded %s %4d.", self.SECTION, lid)

    def get_data(self, lid):  # pragma: no cover
        """Download a wordlist for a specific language."""
        fname = self.raw_dir.download(URL % (self.SECTION, lid), f'{lid}.xml')
        if fname.stat().st_size == 0:
            fname.unlink()
            return False
        return True


def kw_from_element(e: et.Element, fields: Iterable[dataclasses.Field]) -> dict[str, Any]:
    """Parse data from an XML element."""
    res: dict[str, Any] = {'id': str(int(e.find('id').text))}
    for field in fields:
        xml_name = field.metadata.get('xml_name', field.name)
        attr_name = field.name
        conv = field.metadata.get('conv', lambda x: x)

        text = ''
        ee = e.find(xml_name)
        if ee is not None:
            text = e.find(xml_name).text
            if text and not isinstance(text, str):
                text = text.decode('utf8')  # pragma: no cover
        if not text:
            continue

        text = text.strip()
        if not text:
            continue  # pragma: no cover

        res[attr_name] = conv(text) or None
    return res


@dataclasses.dataclass
class Language:  # pylint: disable=R0902
    """A language as given in a BVD XML Wordlist."""
    id: str
    author: str
    name: str = dataclasses.field(metadata={'xml_name': 'language'})
    iso: str = dataclasses.field(metadata={'xml_name': 'silcode'})
    glottocode: Optional[str] = None
    notes: Optional[str] = None
    problems: Optional[str] = None
    classification: Optional[str] = None
    typedby: Optional[str] = None
    checkedby: Optional[str] = None
    source: Optional[str] = None

    @classmethod
    def from_element(cls, e) -> 'Language':
        """Initialize from an XML element."""
        return cls(**kw_from_element(e, dataclasses.fields(cls)))


@dataclasses.dataclass
class Entry:  # pylint: disable=R0902
    """An entry in a BVD XML Wordlist."""
    id: str = dataclasses.field(metadata={'conv': lambda s: str(int(s))})
    word_id: str = dataclasses.field(default='', metadata={'conv': lambda s: str(int(s))})
    word: Optional[str] = None
    name: Optional[str] = dataclasses.field(default=None, metadata={'xml_name': 'item'})
    comment: Optional[str] = dataclasses.field(default=None, metadata={'xml_name': 'annotation'})
    loan: Optional[str] = None
    cognacy: Optional[str] = None
    source_id: Optional[str] = None
    source: Optional[str] = None
    section: Optional[str] = None
    rowids: list[str] = dataclasses.field(default_factory=list)

    @classmethod
    def from_element(cls, e, section) -> 'Entry':
        """Initialize from an XML element."""
        return cls(
            section=section,
            rowids=[],
            **kw_from_element(
                e, [f for f in dataclasses.fields(cls) if f.name not in {'section', 'rowids'}]))

    @property
    def cognates(self) -> list[str]:
        """Possibly multiple cognateset IDs parsed from the cognacy field."""
        # We split into single cognateset IDs on comma, slash and dot.
        return nfilter(re.split('[,/.]', self.cognacy or ''))


class Wordlist:
    """An ABVD-style wordlist, read from XML"""
    def __init__(self, dataset, path: pathlib.Path, log: logging.Logger):
        self.dataset = dataset
        self.log: logging.Logger = log
        e = dataset.raw_dir.read_xml(path.name)
        self.section: str = dataset.SECTION
        records = list(e.findall('./record'))
        self.language: Language = Language.from_element(records[0])
        self.entries: list[Entry] = [
            Entry.from_element(r, self.section) for r in records[1:] if self.is_entry(r)]

    @staticmethod
    def is_entry(r) -> bool:
        """Determine whether XML element r represents a wordlist entry."""
        return bool(getattr(r.find('id'), 'text', None) and getattr(r.find('item'), 'text', None))

    def url(self, path) -> str:  # pylint: disable=C0116
        return f'{BASE_URL}/{self.section}/{path}'

    @property
    def name(self) -> str:  # pylint: disable=C0116
        return f'{self.section} - {self.language.name} - {self.id}'

    @property
    def id(self) -> str:  # pylint: disable=C0116
        return f'{self.section}-{self.language.id}'

    def to_cldf(self, ds, concepts):
        """
        :param ds: the dataset object
        :concepts: a dictionary mapping concept labels to concept ids

        :return: A dataset object, ds.
        """
        source = []
        if self.language.source:
            bib = parse_string(self.language.source, "bibtex")
            try:
                ds.add_sources(*[Source.from_entry(k, e) for k, e in bib.entries.items()])
                source = list(bib.entries.keys())
            except:  # pragma: no cover # noqa: E722  # pylint: disable=W0702
                self.log.warning("Invalid citekey for %s", self.language.id)

        ds.add_language(
            ID=self.language.id,
            Glottocode=self.language.glottocode,
            ISO639P3code=self.language.iso,
            Name=self.language.name,
            author=self.language.author,
            url=self.url(f'language.php?id={self.language.id}'),
            typedby=self.language.typedby,
            checkedby=self.language.checkedby,
            notes=self.language.notes,
            source=";".join(source)
        )

        for entry in self.entries:
            if entry.name is None or len(entry.name) == 0:  # skip empty entries
                continue  # pragma: no cover

            # skip entries marked as incorrect word form due to semantics
            # (x = probably, s = definitely)
            if entry.cognacy and entry.cognacy.lower() in ('s', 'x'):
                continue  # pragma: no cover

            # handle concepts
            cid = concepts.get(entry.word_id)
            if not cid:
                self.dataset.unmapped.add_concept(ID=entry.word_id, Name=entry.word)
                # add it if we don't have it.
                ds.add_concept(ID=entry.word_id, Name=entry.word)
                cid = entry.word_id

            # handle lexemes
            try:
                lex = ds.add_forms_from_value(
                    Local_ID=entry.id,
                    Language_ID=self.language.id,
                    Parameter_ID=cid,
                    Value=entry.name,
                    # set source to entry-level sources if they exist, otherwise use
                    # the language level source.
                    Source=[entry.source] if entry.source else source,
                    Cognacy=entry.cognacy,
                    Comment=entry.comment or '',
                    Loan=bool(entry.loan and len(entry.loan)),
                )
            except:  # NOQA: E722; pragma: no cover
                print(f"ERROR with {entry.id} -- {entry.name}")
                raise

            if lex:
                for cognate_set_id in entry.cognates:
                    match = self.dataset.cognate_pattern.match(cognate_set_id)
                    if not match:  # pragma: no cover
                        self.log.warning(
                            'Invalid cognateset ID for entry %s: %s', entry.id, cognate_set_id)
                        continue
                    # make global cognate set id
                    ds.add_cognate(
                        lexeme=lex[0],
                        Cognateset_ID=f"{slug(entry.word)}-{match.group('id')}",
                        Doubt=bool(match.group('doubt')),
                        Source=['Greenhilletal2008'] if self.section == 'austronesian' else []
                    )
        return ds
