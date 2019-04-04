import re
from collections import OrderedDict, defaultdict
from itertools import chain

import attr
from csvw.metadata import Column
from clldutils.path import copy, Path
from pycldf.dataset import Wordlist
import pyclts.models
from pyconcepticon.api import Concept

from pylexibank.transcription import Analysis, analyze

MD_NAME = 'cldf-metadata.json'
ALT_MD_NAME = 'Wordlist-metadata.json'
ID_PATTERN = re.compile('[A-Za-z0-9_\-]+$')


class Dataset(object):
    def __init__(self, dataset):
        self._count = defaultdict(int)
        self._cognate_count = defaultdict(int)
        self.dataset = dataset

        md = self.dataset.cldf_dir / MD_NAME
        if not md.exists():
            md = self.dataset.cldf_dir / ALT_MD_NAME
            if not md.exists():
                md = self.dataset.cldf_dir / MD_NAME
                copy(Path(__file__).parent / MD_NAME, md)
        self.wl = Wordlist.from_metadata(md)
        default_cldf = Wordlist.from_metadata(Path(__file__).parent / 'cldf-metadata.json')

        self.objects = {}
        self._obj_index = {}
        for cls in [
            self.dataset.lexeme_class,
            self.dataset.language_class,
            self.dataset.concept_class,
            self.dataset.cognate_class,
        ]:
            self.objects[cls.__cldf_table__()] = []
            self._obj_index[cls.__cldf_table__()] = set()

            cols = set(
                col.header for col in self.wl[cls.__cldf_table__()].tableSchema.columns)
            properties = set(
                col.propertyUrl.uri for col in self.wl[cls.__cldf_table__()].tableSchema.columns
                if col.propertyUrl)
            for field in cls.fieldnames():
                try:
                    col = default_cldf[cls.__cldf_table__(), field]
                    #
                    # We added Latitude and Longitude to the default metadata later, and want to
                    # make sure, existing datasets are upgraded silently.
                    #
                    if field in ['Latitude', 'Longitude'] \
                            and cls.__cldf_table__() == 'LanguageTable':
                        properties.add(col.propertyUrl.uri)
                        self.wl[cls.__cldf_table__(), field].propertyUrl = col.propertyUrl
                        self.wl[cls.__cldf_table__(), field].datatype = col.datatype
                except KeyError:
                    col = Column(name=field, datatype="string")
                if (col.propertyUrl and col.propertyUrl.uri not in properties) or \
                        ((not col.propertyUrl) and (field not in cols)):
                    self.wl[cls.__cldf_table__()].tableSchema.columns.append(col)

    def validate(self, log=None):
        return self.wl.validate(log)

    def __getitem__(self, type_):
        return self.wl[type_]

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        for table in ['FormTable', 'CognateTable', 'LanguageTable', 'ParameterTable']:
            self.objects.setdefault(table, [])
        # We only add concepts and languages that are referenced by forms!
        for fk, table in [('Parameter_ID', 'ParameterTable'), ('Language_ID', 'LanguageTable')]:
            refs = set(obj[fk] for obj in self.objects['FormTable'])
            self.objects[table] = [obj for obj in self.objects[table] if obj['ID'] in refs]
        self.write(**self.objects)

    def add_sources(self, *args):
        if not args and self.dataset.raw.joinpath('sources.bib').exists():
            args = self.dataset.raw.read_bib()
        self.wl.sources.add(*args)

    def lexeme_id(self, kw):
        self._count[(kw['Language_ID'], kw['Parameter_ID'])] += 1
        return '{0}-{1}-{2}'.format(
            kw['Language_ID'],
            kw['Parameter_ID'],
            self._count[(kw['Language_ID'], kw['Parameter_ID'])])

    def cognate_id(self, kw):
        self._cognate_count[kw['Form_ID']] += 1
        return '{0}-{1}'.format(kw['Form_ID'], self._cognate_count[kw['Form_ID']])

    def tokenize(self, item, string):
        if self.dataset.tokenizer:
            return self.dataset.tokenizer(item, string)

    def add_lexemes(self, **kw):
        """
        :return: list of dicts corresponding to newly created Lexemes
        """
        lexemes = []

        # Do we have morpheme segmentation on top of phonemes?
        with_morphemes = '+' in self['FormTable', 'Segments'].separator

        for i, form in enumerate(self.dataset.split_forms(kw, kw['Value'])):
            kw_ = kw.copy()
            if form:
                if form != kw_['Value']:
                    self.dataset.log.debug(
                        'iter_forms split: "{0}" -> "{1}"'.format(kw_['Value'], form))
                if form:
                    kw_.setdefault('Segments', self.tokenize(kw_, form) or [])
                    kw_.update(ID=self.lexeme_id(kw), Form=form)
                    lexemes.append(self._add_object(self.dataset.lexeme_class, **kw_))

                    if kw_['Segments']:
                        analysis = self.dataset.tr_analyses.setdefault(
                            kw_['Language_ID'], Analysis())
                        try:
                            segments = kw_['Segments']
                            if with_morphemes:
                                segments = list(chain(*[s.split() for s in segments]))
                            _, _bipa, _sc, _analysis = analyze(segments, analysis)

                            # update the list of `bad_words` if necessary; we precompute a
                            # list of data types in `_bipa` just to make the conditional
                            # checking easier
                            _bipa_types = [type(s) for s in _bipa]
                            if pyclts.models.UnknownSound in _bipa_types or '?' in _sc:
                                self.dataset.tr_bad_words.append(kw_)
                        except ValueError:  # pragma: no cover
                            self.dataset.tr_invalid_words.append(kw_)
                        except (KeyError, AttributeError):  # pragma: no cover
                            print(kw_['Form'], kw_)
                            raise

        return lexemes

    def _add_object(self, cls, **kw):
        # Instantiating an object will trigger potential validators:
        d = attr.asdict(cls(**kw))
        t = cls.__cldf_table__()
        for key in ['ID', 'Language_ID', 'Parameter_ID', 'Cognateset_ID']:
            # stringify/sluggify identifiers:
            if d.get(key) is not None:
                d[key] = '{0}'.format(d[key])
                if not ID_PATTERN.match(d[key]):
                    raise ValueError(
                        'invalid CLDF identifier {0}-{1}: {2}'.format(t, key, d[key]))
        if 'ID' not in d or d['ID'] not in self._obj_index[t]:
            if 'ID' in d:
                self._obj_index[t].add(d['ID'])
            self.objects[t].append(d)
        return d

    def add_cognate(self, lexeme=None, **kw):
        if lexeme:
            kw.setdefault('Form_ID', lexeme['ID'])
            kw.setdefault('Form', lexeme['Form'])
        kw.setdefault('ID', self.cognate_id(kw))
        return self._add_object(self.dataset.cognate_class, **kw)

    def add_language(self, **kw):
        return self._add_object(self.dataset.language_class, **kw)

    def add_languages(self, id_factory=lambda d: d['ID']):
        """
        Add languages as specified in a dataset's etc/languages.csv

        :param id_factory: A callable taking a dict describing a language as argument and returning\
        a value to be used as ID for the language.
        :return: The set of language IDs which have been added.
        """
        ids = set()
        for kw in self.dataset.languages:
            if (not kw.get('Glottocode')) and kw.get('ISO639P3code'):
                kw['Glottocode'] = self.dataset.glottolog.glottocode_by_iso.get(kw['ISO639P3code'])
            kw['ID'] = id_factory(kw)
            ids.add(kw['ID'])
            self.add_language(**kw)
        return ids

    def add_concept(self, **kw):
        if kw.get('Concepticon_ID'):
            kw.setdefault(
                'Concepticon_Gloss',
                self.dataset.concepticon.cached_glosses[int(kw['Concepticon_ID'])])
        return self._add_object(self.dataset.concept_class, **kw)

    def add_concepts(self, id_factory=lambda d: d.number):
        """
        Add concepts as specified in a dataset's associated Concepticon concept list or in
        etc/concepts.csv

        :param id_factory: A callable taking a pyconcepticon.api.Concept object as argument and \
        returning a value to be used as ID for the concept.
        :return: The set of concept IDs which have been added.
        """
        ids, concepts = set(), []
        if self.dataset.conceptlist:
            concepts = self.dataset.conceptlist.concepts.values()
        else:
            fields = Concept.public_fields()
            for i, concept in enumerate(self.dataset.concepts, start=1):
                kw, attrs = {}, {}
                for k, v in concept.items():
                    if k.lower() in fields:
                        kw[k.lower()] = v
                    else:
                        attrs[k.lower()] = v

                if not kw.get('id'):
                    kw['id'] = str(i)
                if not kw.get('number'):
                    kw['number'] = str(i)
                concepts.append(Concept(attributes=attrs, **kw))

        fieldnames = {f.lower(): f for f in self.dataset.concept_class.fieldnames()}
        for c in concepts:
            attrs = dict(
                ID=id_factory(c),
                Name=c.label,
                Concepticon_ID=c.concepticon_id,
                Concepticon_Gloss=c.concepticon_gloss)
            for fl, f in fieldnames.items():
                if fl in c.attributes:
                    attrs[f] = c.attributes[fl]
            ids.add(attrs['ID'])
            self.add_concept(**attrs)
        return ids

    def align_cognates(self,
                       alm=None,
                       cognates=None,
                       column='Segments',
                       method='library'):
        from pylexibank.lingpy_util import iter_alignments

        iter_alignments(
            alm or self,
            cognates or self.objects['CognateTable'],
            column=column,
            method=method)

    def write(self, **kw):
        self.wl.properties.update(self.dataset.metadata.common_props)
        self.wl.properties['rdf:ID'] = self.dataset.id
        self.wl.properties['rdf:type'] = 'http://www.w3.org/ns/dcat#Distribution'
        if self.dataset.github_repo:
            self.wl.properties['dcat:accessURL'] = 'https://github.com/{0}'.format(
                self.dataset.github_repo)
        self.wl.tablegroup.notes.append(OrderedDict([
            ('dc:title', 'environment'),
            ('properties', OrderedDict([
                ('glottolog_version', self.dataset.glottolog.version),
                ('concepticon_version', self.dataset.concepticon.version),
            ]))
        ]))
        self.wl.write(**kw)
