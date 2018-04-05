# coding: utf8
from __future__ import unicode_literals, print_function, division
import re

from six import text_type
from clldutils.misc import xmlchars, slug
from clldutils.path import remove
from clldutils.text import split_text_with_context
from pycldf.sources import Source

from pylexibank.lingpy_util import segmentize
from pylexibank.util import pb
from pylexibank.dataset import Dataset

URL = "https://abvd.shh.mpg.de/utils/save/?type=xml&section=%s&language=%d"
INVALID_LANGUAGE_IDS = {
    'austronesian': [261],  # Duplicate West Futuna list
}


class BVD(Dataset):
    SECTION = None

    def iter_wordlists(self, language_map):
        for xml in pb(list(self.raw.glob('*.xml')), desc='xml-to-wl'):
            wl = Wordlist(self, xml)
            if not wl.language.glottocode:
                if wl.language.id in language_map:
                    wl.language.glottocode = language_map[wl.language.id]
                else:
                    self.unmapped.add_language(
                        id=wl.language.id, name=wl.language.name, iso=wl.language.iso
                    )
            yield wl

    def split_forms(self, item, value):
        value = self.lexemes.get(value, value)
        return [self.clean_form(item, form)
                for form in split_text_with_context(value, separators=',;')]

    def cmd_download(self, **kw):
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

    def get_data(self, lid):
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
                raise ValueError(spec)
            nattr = nattr or attr
            ee = e.find(attr)
            if ee is not None:
                text = e.find(attr).text
                if text and not isinstance(text, text_type):
                    text = text.decode('utf8')
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
        #('pmpcognacy', ''),
    ]

    def __init__(self, e, section):
        self.section = section
        self.rowids = []
        XmlElement.__init__(self, e)

    @property
    def concept_id(self):
        return '%s-%s' % (self.section, int(self.word_id))

    @property
    def concept(self):
        return '%s [%s]' % (self.word, self.section)

    @property
    def cognates(self):
        res = set()
        for comp in re.split(',|/', self.cognacy or ''):
            comp = comp.strip().lower()
            if comp:
                doubt = False
                if comp.endswith('?'):
                    doubt = True
                    comp = comp[:-1].strip()
                res.add(('%s-%s' % (self.word_id, comp), doubt))
        return res


class Wordlist(object):
    def __init__(self, dataset, path):
        self.dataset = dataset
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
        return 'http://language.psy.auckland.ac.nz/%s/%s' % (self.section, path)

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
            concept_key = lambda entry: entry.word_id

        #
        # FIXME: The following should be written to a separate LanguageTable!
        #
        #ds.metadata['dc:creator'] = self.language.author
        #ds.metadata['dc:identifier'] = self.url('language.php?id=%s' % self.language.id)
        #if self.language.typedby:
        #    ds.metadata['dc:contributor'] = self.language.typedby
        #if self.language.checkedby:
        #    ds.metadata['dc:contributor'] = self.language.checkedby
        #if self.language.notes:
        #    ds.metadata['dc:description'] = self.language.notes

        #ds.table.schema.columns['Parameter_local_ID'].valueUrl = \
        #    self.url('word.php?v=1{Parameter_local_ID}')
        #ds.table.schema.columns['Language_local_ID'].valueUrl = \
        #    self.url('language.php?id={Language_local_ID}')

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
            glottocode=self.language.glottocode,
            iso=self.language.iso,
            name=self.language.name)

        for entry in self.entries:
            if entry.name is None or len(entry.name) == 0:  # skip empty entries
                continue

            if not (citekey and source):
                src = entry.e.find('source')
                if src and getattr(src, 'text'):
                    ref = slug(text_type(src.text))
                    ds.add_sources(Source('misc', ref, title=src.text))
            cid = concept_map.get(concept_key(entry))
            if not cid:
                self.dataset.unmapped.add_concept(id=entry.word_id, gloss=entry.word)

            ds.add_concept(ID=entry.word_id, gloss=entry.word, conceptset=cid)
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
                for cognate_set_id, doubt in entry.cognates:
                    ds.add_cognate(lexeme=lex, Cognateset_ID=cognate_set_id, Doubt=doubt)
                # when an entry is split into multiple forms, we only assign cognate
                # sets to the first one!
                break

        segmentize(ds)
        return ds
