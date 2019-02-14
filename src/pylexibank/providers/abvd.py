import re

import attr
from clldutils.misc import slug, nfilter
from clldutils.path import remove
from clldutils.text import split_text_with_context
from pycldf.sources import Source

from pylexibank.util import pb
from pylexibank.dataset import Dataset, Language

BASE_URL = "https://abvd.shh.mpg.de"
URL = BASE_URL + "/utils/save/?type=xml&section=%s&language=%d"
INVALID_LANGUAGE_IDS = {
    'austronesian': [261],  # Duplicate West Futuna list
}


@attr.s
class BVDLanguage(Language):
    author = attr.ib(default=None)
    url = attr.ib(default=None)
    typedby = attr.ib(default=None)
    checkedby = attr.ib(default=None)
    notes = attr.ib(default=None)


class BVD(Dataset):
    SECTION = None
    language_class = BVDLanguage
    cognate_pattern = re.compile('\s*(?P<id>([A-z]?[0-9]+|[A-Z]))\s*(?P<doubt>\?+)?\s*$')

    def iter_wordlists(self, language_map, log):
        for xml in pb(sorted(self.raw.glob('*.xml'), key=lambda p: int(p.stem)), desc='xml-to-wl'):
            wl = Wordlist(self, xml, log)
            if not wl.language.glottocode:
                if wl.language.id in language_map:
                    wl.language.glottocode = language_map[wl.language.id]
                else:  # pragma: no cover
                    self.unmapped.add_language(
                        ID=wl.language.id,
                        Name=wl.language.name,
                        ISO639P3code=wl.language.iso
                    )
            yield wl

    def split_forms(self, item, value):
        value = self.lexemes.get(value, value)
        return [self.clean_form(item, form)
                for form in split_text_with_context(value, separators=',;')]

    def cmd_download(self, **kw):  # pragma: no cover
        assert self.SECTION in ['austronesian', 'mayan', 'utoaztecan']
        self.log.info('ABVD section set to %s' % self.SECTION)
        for fname in self.raw.iterdir():
            remove(fname)
        language_ids = [
            i for i in range(1, 2000)
            if i not in INVALID_LANGUAGE_IDS.get(self.SECTION, [])]

        for lid in language_ids:
            if not self.get_data(lid):
                self.log.warn("No content for %s %d. Ending." % (self.SECTION, lid))
                break

    def get_data(self, lid):  # pragma: no cover
        fname = self.raw.download(URL % (self.SECTION, lid), '%s.xml' % lid, log=self.log)
        if fname.stat().st_size == 0:
            remove(fname)
            return False
        return True


class XmlElement(object):
    __attr_map__ = []

    def __init__(self, e):
        self.id = '%s' % int(e.find('id').text)
        self.e = e
        for spec in self.__attr_map__:
            if len(spec) == 2:
                attr, nattr = spec
                conv = None
            elif len(spec) == 3:
                attr, nattr, conv = spec
            else:
                raise ValueError(spec)  # pragma: no cover
            nattr = nattr or attr
            ee = e.find(attr)
            if ee is not None:
                text = e.find(attr).text
                if text and not isinstance(text, str):
                    text = text.decode('utf8')  # pragma: no cover
            else:
                text = ''
            if text:
                text = text.strip()

            if text and conv:
                text = conv(text)

            setattr(self, nattr, text or None)


class Language(XmlElement):
    __attr_map__ = [
        ('author', ''),
        ('language', 'name'),
        ('silcode', 'iso'),
        ('glottocode', ''),
        ('notes', ''),
        ('problems', ''),
        ('classification', ''),
        ('typedby', ''),
        ('checkedby', ''),
    ]

    def __init__(self, e):
        XmlElement.__init__(self, e)


class Entry(XmlElement):
    __attr_map__ = [
        ('id', '', lambda s: '%s' % int(s)),
        ('word_id', '', lambda s: '%s' % int(s)),
        ('word', ''),
        ('item', 'name'),
        ('annotation', 'comment'),
        ('loan', ''),
        ('cognacy', ''),
    ]

    def __init__(self, e, section):
        self.section = section
        self.rowids = []
        XmlElement.__init__(self, e)

    @property
    def cognates(self):
        # We split into single cognateset IDs on comma, slash and dot.
        return nfilter(re.split('[,/.]', self.cognacy or ''))


class Wordlist(object):
    def __init__(self, dataset, path, log):
        self.dataset = dataset
        self.log = log
        e = dataset.raw.read_xml(path.name)
        self.section = dataset.SECTION
        records = list(e.findall('./record'))
        self.language = Language(records[0])
        self.entries = [Entry(r, self.section) for r in records[1:] if self.is_entry(r)]

    @staticmethod
    def is_entry(r):
        return getattr(r.find('id'), 'text', None) \
            and getattr(r.find('item'), 'text', None)

    def url(self, path):
        return '%s/bantu/%s/%s' % (BASE_URL, self.section, path)

    @property
    def name(self):
        return '%s - %s - %s' % (self.section, self.language.name, self.id)

    @property
    def id(self):
        return '%s-%s' % (self.section, self.language.id)

    def md(self):
        return dict(properties={
            k: getattr(self.language, k, None)
            for k in 'id name author notes problems typedby checkedby'.split()})

    def to_cldf(self, ds, concept_map, citekey=None, source=None, concept_key=None):
        if concept_key is None:
            def concept_key(entry):
                return entry.word_id

        ref = None
        if citekey and source:
            ref = citekey
            for r in ref.split(";"):
                for s in source:
                    if isinstance(s, Source):
                        ds.add_sources(s)
                    else:
                        ds.add_sources(Source('misc', r, title=s))

        ds.add_language(
            ID=self.language.id,
            Glottocode=self.language.glottocode,
            ISO639P3code=self.language.iso,
            Name=self.language.name,
            author=self.language.author,
            url=self.url('language.php?id=%s' % self.language.id),
            typedby=self.language.typedby,
            checkedby=self.language.checkedby,
            notes=self.language.notes,
        )

        for entry in self.entries:
            if entry.name is None or len(entry.name) == 0:  # skip empty entries
                continue  # pragma: no cover

            if entry.cognacy and (
                    's' == entry.cognacy.lower() or 'x' in entry.cognacy.lower()):
                # skip entries marked as incorrect word form due to semantics
                # (x = probably, s = definitely)
                continue  # pragma: no cover

            if not (citekey and source):
                src = entry.e.find('source')
                if (src is not None) and getattr(src, 'text'):
                    ref = slug(str(src.text))
                    ds.add_sources(Source('misc', ref, title=src.text))
            cid = concept_map.get(concept_key(entry))
            if not cid:
                self.dataset.unmapped.add_concept(ID=entry.word_id, Name=entry.word)

            ds.add_concept(ID=entry.word_id, Name=entry.word, Concepticon_ID=cid)
            for lex in ds.add_lexemes(
                Language_ID=self.language.id,
                Parameter_ID=entry.word_id,
                Value=entry.name,
                Source=[ref],
                Cognacy=entry.cognacy,
                Comment=entry.comment or '',
                Loan=True if entry.loan and len(entry.loan) else False,
                Local_ID=entry.id,
            ):
                for cognate_set_id in entry.cognates:
                    match = self.dataset.cognate_pattern.match(cognate_set_id)
                    if not match:  # pragma: no cover
                        self.log.warn('Invalid cognateset ID: {0}'.format(cognate_set_id))
                    else:
                        ds.add_cognate(
                            lexeme=lex,
                            Cognateset_ID=match.group('id'),
                            Doubt=bool(match.group('doubt')))
                # when an entry is split into multiple forms, we only assign cognate
                # sets to the first one!
                break

        return ds
