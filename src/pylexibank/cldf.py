import re
import logging
import pathlib
import itertools
import collections
import collections.abc
import pkg_resources

import attr
from csvw.metadata import Column
from pycldf.dataset import Wordlist
import pyclts.models

from cldfbench.cldf import CLDFWriter
from cldfbench.util import iter_requirements

from pylexibank.transcription import Analysis, analyze
from pylexibank.util import iter_repl, get_concepts, get_ids_and_attrs

__all__ = ['LexibankWriter']
log = logging.getLogger('pylexibank')

MD_NAME = 'cldf-metadata.json'
ID_PATTERN = re.compile(r'[A-Za-z0-9_\-]+$')


class LexibankWriter(CLDFWriter):
    def __init__(self, **kw):
        super().__init__(**kw)
        self._count = collections.defaultdict(int)
        self._cognate_count = collections.defaultdict(int)

    def write(self, **kw):
        from pylexibank import ENTRY_POINT

        super().write(**kw)
        # We rewrite requirements.txt, excluding all lexibank dataset modules:
        exclude = {'egg=' + ep.module_name for ep in pkg_resources.iter_entry_points(ENTRY_POINT)}
        reqs = []
        for req in iter_requirements():
            if not any(mod in req for mod in exclude):
                reqs.append(req)

        self.cldf_spec.dir.joinpath('requirements.txt').write_text('\n'.join(reqs), encoding='utf8')

    def __enter__(self):
        super().__enter__()
        default_cldf = Wordlist.from_metadata(pathlib.Path(__file__).parent / MD_NAME)

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
        for table in ['FormTable', 'LanguageTable', 'ParameterTable']:
            self.objects.setdefault(table, [])
        if not self.objects.get('CognateTable'):
            self.cldf.tablegroup.tables = [
                t for t in self.cldf.tables if str(t.url) != 'cognates.csv']
            if 'CognateTable' in self.objects:
                del self.objects['CognateTable']

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

    def tokenize(self, item, string, **kw):
        if self.dataset.tokenizer:
            return self.dataset.tokenizer(item, string, **kw)

    def add_form_with_segments(self, **kw):
        """
        :return: dict with the newly created lexeme
        """
        # Do we have morpheme segmentation on top of phonemes?
        with_morphemes = '+' in self['FormTable', 'Segments'].separator

        language, concept, value, form, segments = (kw.get(v) for v in [
            'Language_ID', 'Parameter_ID', 'Value', 'Form', 'Segments'])

        # check for required kws
        if not all([language, concept, value, form, segments]):
            raise ValueError('language, concept, value, form, and segments must be supplied')

        # Correct segments according to mapping in etc/segments.csv:
        for k, v in self.dataset.segments.items():
            segments = list(iter_repl(segments, k.split(), v.split()))
        kw['Segments'] = segments
        kw.update(ID=self.lexeme_id(kw), Form=form)
        lexeme = self._add_object(self.dataset.lexeme_class, **kw)

        analysis = self.dataset.tr_analyses.setdefault(kw['Language_ID'], Analysis())
        try:
            segments = kw['Segments']
            if with_morphemes:
                segments = list(itertools.chain(*[s.split() for s in segments]))
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
            profile = kw.pop('profile', None)
            kw.setdefault(
                'Segments',
                self.tokenize(kw, form, **(dict(profile=profile) if profile else {})) or [])
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
        #
        # FIXME: check whether certain attributes should not be written to the table.
        #
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
        """
        Add a row to `CognateTable`.

        :param lexeme: An optional `FormTable` row (i.e. `dict`) to lookup lexeme data.
        :param kw: Attribute data to intialise a `self.dataset.cognate class` instance.
        :return: The (possibly augmented) instance data as `dict`.
        """
        if lexeme:
            if not isinstance(lexeme, collections.abc.Mapping):  # pragma: no cover
                raise TypeError('lexeme must be a mapping (`dict`) of lexeme attributes')
            kw.setdefault('Form_ID', lexeme['ID'])
            kw.setdefault('Form', lexeme['Form'])

        kw.setdefault('ID', self.cognate_id(kw))
        return self._add_object(self.dataset.cognate_class, **kw)

    def add_language(self, **kw):
        if (not getattr(self.args, 'dev', False)) and 'Glottocode' in kw \
                and hasattr(self.args, 'glottolog') \
                and kw['Glottocode'] in self.args.glottolog.api.cached_languoids:
            glang = self.args.glottolog.api.cached_languoids[kw['Glottocode']]
            for key, attribute in [
                ('Latitude', 'latitude'),
                ('Longitude', 'longitude'),
                ('Glottolog_Name', 'name'),
                ('ISO639P3code', 'iso')
            ]:
                if kw.get(key) is None:
                    kw[key] = getattr(glang, attribute)
            if kw.get('Family') is None:
                kw['Family'] = glang.lineage[0][0] if glang.lineage else glang.name
            if kw.get('Macroarea') is None:
                kw['Macroarea'] = glang.macroareas[0].name if glang.macroareas else None

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
        ids = collections.OrderedDict()
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
            gloss = self.dataset.concepticon.cached_glosses[int(kw['Concepticon_ID'])]
            if kw.get('Concepticon_Gloss') and kw.get('Concepticon_Gloss') != gloss:
                raise ValueError('Concepticon ID / Gloss mismatch %s != %s' % (
                    kw.get('Concepticon_Gloss'), gloss
                ))
            kw['Concepticon_Gloss'] = gloss
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

        ids, attrss = get_ids_and_attrs(
            # Read pyconcepticon.Concept instances either from a conceptlist in Concepticon, or from
            # etc/concepts.csv:
            get_concepts(self.dataset.conceptlists, self.dataset.concepts),
            {f.lower(): f for f in self.dataset.concept_class.fieldnames()},
            id_factory,
            lookup_factory,
        )
        for attrs in attrss:
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
