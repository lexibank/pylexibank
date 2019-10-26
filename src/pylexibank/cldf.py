import re
from collections import defaultdict, OrderedDict
from itertools import chain
from pathlib import Path
import logging

import attr
from csvw.metadata import Column
from pycldf.dataset import Wordlist
import pyclts.models
from pyconcepticon.api import Concept

from cldfbench.cldf import CLDFWriter

from pylexibank.transcription import Analysis, analyze

__all__ = ['LexibankWriter']
log = logging.getLogger('pylexibank')

MD_NAME = 'cldf-metadata.json'
ID_PATTERN = re.compile('[A-Za-z0-9_\-]+$')


class LexibankWriter(CLDFWriter):
    def __init__(self, **kw):
        super().__init__(**kw)
        self._count = defaultdict(int)
        self._cognate_count = defaultdict(int)

    def __enter__(self):
        super().__enter__()
        default_cldf = Wordlist.from_metadata(Path(__file__).parent / MD_NAME)

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
                col.header for col in self.cldf[cls.__cldf_table__()].tableSchema.columns)
            properties = set(
                col.propertyUrl.uri for col in self.cldf[cls.__cldf_table__()].tableSchema.columns
                if col.propertyUrl)
            for field in cls.fieldnames():
                try:
                    col = default_cldf[cls.__cldf_table__(), field]
                    #
                    # We added Latitude and Longitude to the default metadata later, and want to
                    # make sure, existing datasets are upgraded silently.
                    #
                    if field in ['Latitude', 'Longitude'] \
                            and cls.__cldf_table__() == 'LanguageTable':  # pragma: no cover
                        properties.add(col.propertyUrl.uri)
                        self.cldf[cls.__cldf_table__(), field].propertyUrl = col.propertyUrl
                        self.cldf[cls.__cldf_table__(), field].datatype = col.datatype
                except KeyError:
                    col = Column(name=field, datatype="string")
                if (col.propertyUrl and col.propertyUrl.uri not in properties) or \
                        ((not col.propertyUrl) and (field not in cols)):
                    self.cldf[cls.__cldf_table__()].tableSchema.columns.append(col)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        for table in ['FormTable', 'CognateTable', 'LanguageTable', 'ParameterTable']:
            self.objects.setdefault(table, [])
        # We only add concepts and languages that are referenced by forms!
        for fk, table in [('Parameter_ID', 'ParameterTable'), ('Language_ID', 'LanguageTable')]:
            refs = set(obj[fk] for obj in self.objects['FormTable'])
            self.objects[table] = [obj for obj in self.objects[table] if obj['ID'] in refs]
        super().__exit__(exc_type, exc_val, exc_tb)

    def add_sources(self, *args):
        if not args and self.dataset.raw_dir.joinpath('sources.bib').exists():
            args = self.dataset.raw_dir.read_bib()
        self.cldf.sources.add(*args)

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

    def add_form_with_segments(self, **kw):
        """
        :return: dict with the newly created lexeme
        """
        # Do we have morpheme segmentation on top of phonemes?
        with_morphemes = '+' in self['FormTable', 'Segments'].separator

        language, concept, value, form, segments = [kw.get(v) for v in [
            'Language_ID', 'Parameter_ID', 'Value', 'Form', 'Segments']]

        # check for required kws
        if language is None or concept is None or value is None \
                or form is None or segments is None:
            raise ValueError('language, concept, value, form, and segments must be supplied')
        kw.setdefault('Segments', segments)
        kw.update(ID=self.lexeme_id(kw), Form=form)
        lexeme = self._add_object(self.dataset.lexeme_class, **kw)

        analysis = self.dataset.tr_analyses.setdefault(kw['Language_ID'], Analysis())
        try:
            segments = kw['Segments']
            if with_morphemes:
                segments = list(chain(*[s.split() for s in segments]))
            _, _bipa, _sc, _analysis = analyze(self.args.clts.api, segments, analysis)

            # update the list of `bad_words` if necessary; we precompute a
            # list of data types in `_bipa` just to make the conditional
            # checking easier
            _bipa_types = [type(s) for s in _bipa]
            if pyclts.models.UnknownSound in _bipa_types or '?' in _sc:
                self.dataset.tr_bad_words.append(kw)
        except ValueError:  # pragma: no cover
            self.dataset.tr_invalid_words.append(kw)
        except (KeyError, AttributeError):  # pragma: no cover
            print(kw['Form'], kw)
            raise
        return lexeme

    def add_form(self, with_morphemes=False, **kw):
        """
        :return: dict with the newly created form
        """
        language, concept, value, form = [kw.get(v) for v in [
            'Language_ID', 'Parameter_ID', 'Value', 'Form']]

        # check for required kws
        if language is None or concept is None or value is None \
                or form is None:
            raise ValueError('language, concept, value, and form must be supplied')

        # check for kws not allowed
        if 'Segments' in kw:
            raise ValueError('segmented data must be passed with add_form_with_segments')

        # point to difference in value and form
        if form != value:
            log.debug('iter_forms split: "{0}" -> "{1}"'.format(value, form))

        if form:
            # try to segment the data now
            kw.setdefault('Segments', self.tokenize(kw, form) or [])
            if kw['Segments']:
                return self.add_form_with_segments(**kw)

            kw.update(ID=self.lexeme_id(kw), Form=form)
            return self._add_object(self.dataset.lexeme_class, **kw)

    def add_forms_from_value(self, split_value=None, **kw):
        """
        :return: list of dicts corresponding to newly created Lexemes
        """
        lexemes = []

        if 'Segments' in kw:
            raise ValueError('segmented data must be passed with add_form_with_segments')
        if 'Form' in kw:
            raise ValueError('forms must be passed with add_form')

        svkw = {}
        if split_value is None:
            split_value = self.dataset.form_spec.split
            svkw = dict(lexemes=self.dataset.lexemes)

        # Do we have morpheme segmentation on top of phonemes?
        with_morphemes = '+' in self['FormTable', 'Segments'].separator

        for i, form in enumerate(split_value(kw, kw['Value'], **svkw)):
            kw_ = kw.copy()
            kw_['Form'] = form
            if kw_['Form']:
                kw_ = self.add_form(with_morphemes=with_morphemes, **kw_)
                if kw_:
                    lexemes.append(kw_)

        return lexemes

    def add_lexemes(self, split_value=None, **kw):
        """
        :return: list of dicts corresponding to newly created Lexemes
        """
        return self.add_forms_from_value(split_value=split_value, **kw)

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

    def add_languages(self, id_factory='ID', lookup_factory=None):
        """
        Add languages as specified in a dataset's etc/languages.csv

        :param id_factory: A callable taking a dict describing a language as argument and returning\
        a value to be used as ID for the language or a `str` specifying a key in the language \
        `dict`.
        :param lookup_factory: A callable taking a language `dict` and returning a reverse \
        lookup key to associate the generated ID with (or a `str` specifying a key in the language \
        `dict`).
        :return: The `list` of language IDs which have been added, if no `lookup_factory` was \
        passed, otherwise an `OrderedDict`, mapping lookup to ID.
        """
        assert callable(id_factory) or isinstance(id_factory, str)
        ids = OrderedDict()
        for i, kw in enumerate(self.dataset.languages):
            if (not kw.get('Glottocode')) and kw.get('ISO639P3code'):
                kw['Glottocode'] = self.dataset.glottolog.glottocode_by_iso.get(kw['ISO639P3code'])
            kw['ID'] = id_factory(kw) if callable(id_factory) else kw[id_factory]
            if lookup_factory is None:
                key = i
            else:
                key = lookup_factory(kw) if callable(lookup_factory) else kw[lookup_factory]
            ids[key] = kw['ID']
            self.add_language(**kw)
        return ids if lookup_factory else list(ids.values())

    def add_concept(self, **kw):
        if kw.get('Concepticon_ID'):
            kw.setdefault(
                'Concepticon_Gloss',
                self.dataset.concepticon.cached_glosses[int(kw['Concepticon_ID'])])
        return self._add_object(self.dataset.concept_class, **kw)

    def add_concepts(self, id_factory=lambda d: d.number, lookup_factory=None):
        """
        Add concepts as specified in a dataset's associated Concepticon concept list or in
        etc/concepts.csv

        :param id_factory: A callable taking a pyconcepticon.api.Concept object as argument and \
        returning a value to be used as ID for the concept.
        :param lookup_factory: A callable taking a `dict` object and returning a reverse \
        lookup key to associate the generated ID with (or a `str` specifying an attribute in \
        `Concept`).
        :return: The `list` of concept IDs which have been added, if no `lookup_factory` was \
        passed, otherwise an `OrderedDict`, mapping lookup to ID.
        """
        assert callable(id_factory) or isinstance(id_factory, str)

        # Read pyconcepticon.Concept instances either from a conceptlist in Concepticon, or from
        # etc/concepts.csv:
        ids, concepts = OrderedDict(), []
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

        # Now turn the concepts into `dict`s suitable to instantiate `self.dataset.concept_class`:
        fieldnames = {f.lower(): f for f in self.dataset.concept_class.fieldnames()}
        for i, c in enumerate(concepts):
            try:
                # `id_factory` might expect a pyconcepticon.Concept instance as input:
                id_ = id_factory(c) if callable(id_factory) else getattr(c, id_factory)
            except AttributeError:
                id_ = None
            attrs = dict(
                ID=id_,
                Name=c.label,
                Concepticon_ID=c.concepticon_id,
                Concepticon_Gloss=c.concepticon_gloss)
            for fl, f in fieldnames.items():
                if fl in c.attributes:
                    attrs[f] = c.attributes[fl]
            if attrs['ID'] is None:
                attrs['ID'] = id_factory(attrs) if callable(id_factory) else attrs[id_factory]
            if lookup_factory is None:
                key = i
            else:
                key = lookup_factory(attrs) if callable(lookup_factory) else attrs[lookup_factory]
            ids[key] = attrs['ID']
            self.add_concept(**attrs)
        return ids if lookup_factory else list(ids.values())

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
