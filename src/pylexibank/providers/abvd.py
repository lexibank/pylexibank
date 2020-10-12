import re

import attr
from clldutils.misc import slug, nfilter
from pycldf.sources import Source
from pybtex.database import parse_string  # dependency of pycldf, so should be installed.
from pylexibank import Dataset, Language

BASE_URL = "https://abvd.shh.mpg.de"
URL = BASE_URL + "/utils/save/?type=xml&section=%s&language=%d"


@attr.s
class BVDLanguage(Language):
    author = attr.ib(default=None)
    url = attr.ib(default=None)
    typedby = attr.ib(default=None)
    checkedby = attr.ib(default=None)
    notes = attr.ib(default=None)
    source = attr.ib(default=None)


class BVD(Dataset):
    SECTION = None
    invalid_ids = []
    max_language_id = 50  # maximum language id to look for.
    language_class = BVDLanguage
    cognate_pattern = re.compile(r'''\s*(?P<id>([A-z]?[0-9]+|[A-Z]))\s*(?P<doubt>\?+)?\s*$''')

    def iter_wordlists(self, log=None):
        for xml in sorted(self.raw_dir.glob('*.xml'), key=lambda p: int(p.stem)):
            yield Wordlist(self, xml, log)

    def cmd_download(self, args):  # pragma: no cover
        assert self.SECTION in ['austronesian', 'mayan', 'utoaztecan']
        args.log.info('ABVD section set to %s' % self.SECTION)
        # remove
        for fname in self.raw_dir.iterdir():
            fname.unlink()

        for lid in range(1, self.max_language_id + 1):
            if lid in self.invalid_ids:
                args.log.warn("Skipping %s %d - invalid ID" % (self.SECTION, lid))
                continue

            if not self.get_data(lid):
                args.log.warn("No content for %s %d. Ending." % (self.SECTION, lid))
                break
            else:
                args.log.info("Downloaded %s %4d." % (self.SECTION, lid))

    def get_data(self, lid):  # pragma: no cover
        fname = self.raw_dir.download(URL % (self.SECTION, lid), '%s.xml' % lid)
        if fname.stat().st_size == 0:
            fname.unlink()
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
        ('source', ''),
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
        ('source_id', ''),
        ('source', ''),
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
        e = dataset.raw_dir.read_xml(path.name)
        self.section = dataset.SECTION
        records = list(e.findall('./record'))
        self.language = Language(records[0])
        self.entries = [Entry(r, self.section) for r in records[1:] if self.is_entry(r)]

    @staticmethod
    def is_entry(r):
        return getattr(r.find('id'), 'text', None) \
            and getattr(r.find('item'), 'text', None)

    def url(self, path):
        return '%s/%s/%s' % (BASE_URL, self.section, path)

    @property
    def name(self):
        return '%s - %s - %s' % (self.section, self.language.name, self.id)

    @property
    def id(self):
        return '%s-%s' % (self.section, self.language.id)

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
            except:  # noqa: E722
                self.log.warn("Invalid citekey for %s" % self.language.id)

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
                    Loan=True if entry.loan and len(entry.loan) else False,
                )
            except:  # NOQA: E722; pragma: no cover
                print("ERROR with %r -- %r" % (entry.id, entry.name))
                raise

            if lex:
                for cognate_set_id in entry.cognates:
                    match = self.dataset.cognate_pattern.match(cognate_set_id)
                    if not match:  # pragma: no cover
                        self.log.warn('Invalid cognateset ID for entry {0}: {1}'.format(
                            entry.id, cognate_set_id))
                    else:
                        # make global cognate set id
                        cs_id = "%s-%s" % (slug(entry.word), match.group('id'))

                        ds.add_cognate(
                            lexeme=lex[0],
                            Cognateset_ID=cs_id,
                            Doubt=bool(match.group('doubt')),
                            Source=['Greenhilletal2008'] if self.section == 'austronesian' else []
                        )

        return ds
