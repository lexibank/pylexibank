"""
Functionality bridging cldfbench and pycldf datasets.
"""
import re
import logging
import pathlib
import textwrap
import functools
import itertools
import collections
import collections.abc
import dataclasses
from typing import Optional, Any, Callable, Union

from csvw.metadata import Column
from pycldf.dataset import Wordlist
from pycldf.sources import Source
import pyclts.models
from pyconcepticon.api import Concept

from cldfbench.cldf import CLDFWriter
from cldfbench.util import iter_requirements, get_entrypoints

from pylexibank.transcription import Analysis, analyze, valid_sequence, CachedSegments
from pylexibank.util import iter_repl, get_concepts, get_ids_and_attrs, ENTRY_POINT
from pylexibank.lingpy_util import iter_alignments

__all__ = ['LexibankWriter']
log = logging.getLogger('pylexibank')

MD_NAME = 'cldf-metadata.json'
ID_PATTERN = re.compile(r'[A-Za-z0-9_\-]+$')


@dataclasses.dataclass
class Options:
    """The Lexibank writer object is somewhat configurable."""
    keep_languages: bool = False
    keep_parameters: bool = False


class LexibankWriter(CLDFWriter):
    """
    A Lexibank-specific CLDFWriter.
    """
    def __init__(self, dataset=None, **kw):
        super().__init__(dataset=dataset, **kw)
        self._count = collections.defaultdict(int)
        self._cognate_count = collections.defaultdict(int)
        self.options = Options(**getattr(dataset, 'writer_options', {}))

    def write(self, **kw):
        """Write the collected data to disk."""
        self.cldf.add_provenance(wasGeneratedBy=[
            collections.OrderedDict([
                ('dc:title', "lingpy-rcParams"), ('dc:relation', 'lingpy-rcParams.json')])])

        super().write(**kw)
        # We rewrite requirements.txt, excluding all lexibank dataset modules:
        exclude = {'egg=' + ep.load().__module__ for ep in get_entrypoints(ENTRY_POINT)}
        reqs = []
        for req in iter_requirements():
            if not any(mod in req for mod in exclude):
                reqs.append(req)

        self.cldf_spec.dir.joinpath('requirements.txt').write_text('\n'.join(reqs), encoding='utf8')

    def __enter__(self):
        super().__enter__()
        default_cldf = Wordlist.from_metadata(pathlib.Path(__file__).parent / MD_NAME)

        self._obj_index = {}  # pylint: disable=W0201
        for cls in [
            self.dataset.lexeme_class,
            self.dataset.language_class,
            self.dataset.concept_class,
            self.dataset.cognate_class,
        ]:
            if cls.__doc__:
                self.cldf[cls.__cldf_table__()].common_props['dc:description'] = \
                    textwrap.dedent(cls.__doc__)

            self.objects[cls.__cldf_table__()] = []
            self._obj_index[cls.__cldf_table__()] = set()

            cols = set(
                col.header for col in self.cldf[cls.__cldf_table__()].tableSchema.columns)
            properties = set(
                col.propertyUrl.uri for col in self.cldf[cls.__cldf_table__()].tableSchema.columns
                if col.propertyUrl)
            fields_dict = {f.name: f for f in dataclasses.fields(cls)}
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
                    kw = dict(fields_dict[field].metadata.items())
                    kw.setdefault('datatype', 'string')
                    kw.setdefault('name', field)
                    col = Column.fromvalue(kw)
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
        for fk, table in [('Parameter_ID', 'ParameterTable'), ('Language_ID', 'LanguageTable')]:
            if (table == 'ParameterTable' and self.options.keep_parameters) or \
                    (table == 'LanguageTable' and self.options.keep_languages):
                continue  #
            # If opt-in, we only add concepts and languages that are referenced by forms.
            refs = set(obj[fk] for obj in self.objects['FormTable'])
            self.objects[table] = [obj for obj in self.objects[table] if obj['ID'] in refs]
        super().__exit__(exc_type, exc_val, exc_tb)

    @functools.cached_property
    def with_morphemes(self) -> bool:
        """Do we have morpheme segmentation on top of phonemes?"""
        return '+' in self['FormTable', 'Segments'].separator

    def add_sources(self, *args: Union[str, Source]):
        """Add sources to the dataset."""
        if not args and self.dataset.raw_dir.joinpath('sources.bib').exists():
            args = self.dataset.raw_dir.read_bib()
        self.cldf.sources.add(*args)

    def lexeme_id(self, kw: dict[str, Any]) -> str:
        """A unique ID for a lexeme."""
        self._count[(kw['Language_ID'], kw['Parameter_ID'])] += 1
        return (f"{kw['Language_ID']}-{kw['Parameter_ID']}-"
                f"{self._count[(kw['Language_ID'], kw['Parameter_ID'])]}")

    def cognate_id(self, kw) -> str:
        """A unique cognate ID."""
        self._cognate_count[kw['Form_ID']] += 1
        return f"{kw['Form_ID']}-{self._cognate_count[kw['Form_ID']]}"

    def tokenize(self, item, string, **kw) -> Optional[list[str]]:
        """Tokenize a string."""
        if self.dataset.tokenizer:
            return self.dataset.tokenizer(item, string, **kw)
        return None

    def analyze_segments(self, form_data: dict[str, Any]):
        """Analyze the segments, logging problems."""
        analysis = self.dataset.tr_analyses.setdefault(form_data['Language_ID'], Analysis())
        try:
            segments = form_data['Segments']
            if self.with_morphemes:
                segments = list(itertools.chain(*[s.split() for s in segments]))
            valid = valid_sequence(segments)
            _, _bipa, _sc, _analysis = analyze(self.args.clts.api, segments, analysis)

            # update the list of `bad_words` if necessary; we precompute a
            # list of data types in `_bipa` just to make the conditional
            # checking easier
            _bipa_types = [type(s) for s in _bipa]
            if (pyclts.models.UnknownSound in _bipa_types) or '?' in _sc or not valid:
                self.dataset.tr_bad_words.append(form_data)
        except ValueError:  # pragma: no cover
            self.dataset.tr_invalid_words.append(form_data)
        except (KeyError, AttributeError):  # pragma: no cover
            print(form_data['Form'], form_data)
            raise

    def add_form_with_segments(self, **kw):
        """
        :return: dict with the newly created lexeme
        """
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
        self.analyze_segments(kw)
        return self._add_object(self.dataset.lexeme_class, **kw)

    def add_form(self, **kw):
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
            log.debug('iter_forms split: "%s" -> "%s"', value, form)

        if form and form not in self.dataset.form_spec.missing_data:
            # try to segment the data now
            profile = kw.pop('profile', None)
            kw.setdefault(
                'Segments',
                self.tokenize(kw, form, **({'profile': profile} if profile else {})) or [])
            if kw['Segments']:
                return self.add_form_with_segments(**kw)

            kw.update(ID=self.lexeme_id(kw), Form=form)
            return self._add_object(self.dataset.lexeme_class, **kw)
        return None  # pragma: no cover

    def add_forms_from_value(self, split_value=None, **kw) -> list[dict]:
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
            svkw = {'lexemes': self.dataset.lexemes}

        for form in split_value(kw, kw['Value'], **svkw):
            kw_ = kw.copy()
            kw_['Form'] = form
            if kw_['Form']:
                kw_ = self.add_form(**kw_)
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
        d = dataclasses.asdict(cls(**kw))
        t = cls.__cldf_table__()
        for key in ['ID', 'Language_ID', 'Parameter_ID', 'Cognateset_ID']:
            # stringify/sluggify identifiers:
            if d.get(key) is not None:
                d[key] = f'{d[key]}'
                if not ID_PATTERN.match(d[key]):
                    raise ValueError(f'invalid CLDF identifier {t}-{key}: {d[key]}')
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
        """Add a language to the dataset based on the data in `kw`."""
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

    def add_languages(
            self,
            id_factory: Union[str, Callable[[dict[str, Any]], str]] = 'ID',
            lookup_factory: Union[None, str, Callable[[dict[str, Any]], str]] = None,
    ) -> Union[collections.OrderedDict[str, str], list[str]]:
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
        """Add a concept to the dataset using using the data in `kw`."""
        if kw.get('Concepticon_ID'):
            gloss = self.dataset.concepticon.cached_glosses[int(kw['Concepticon_ID'])]
            if kw.get('Concepticon_Gloss') and kw.get('Concepticon_Gloss') != gloss:
                raise ValueError(
                    f"Concepticon ID / Gloss mismatch {kw.get('Concepticon_Gloss')} != {gloss}")
            kw['Concepticon_Gloss'] = gloss
        return self._add_object(self.dataset.concept_class, **kw)

    def add_concepts(
            self,
            id_factory: Union[str, Callable[[Concept], str]] = lambda d: d.number,
            lookup_factory: Union[None, str, Callable[[Union[Concept, dict[str, Any]]], str]] = None
    ):
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
                       cognates: Optional[list[dict[str, Any]]] = None,
                       column: str = 'Segments',
                       method: str = 'library'):
        """Add alignments to cognates."""
        # iter_alignments does **not** yield anything but aligns the cognates "in-place", i.e.
        # adding the alignments to the cognate dicts.
        iter_alignments(
            alm or self,
            cognates or self.objects['CognateTable'],
            column=column,
            method=method)
