"""
A Lexibank-specific cldfbench.Dataset subclass.
"""
import argparse
import pathlib
import functools
import collections
import dataclasses
import unicodedata
from typing import Optional, Protocol, Union

from csvw.dsv import reader
from clldutils import jsonlib
from pyconcepticon.models import Conceptlist
from pyglottolog.languoids import Glottocode

from segments import Tokenizer

from cldfbench.dataset import Dataset as BaseDataset
from cldfbench.cldf import CLDFSpec

from pylexibank.util import jsondump, log_dump
from pylexibank import cldf
from pylexibank import models
from pylexibank import transcription
from pylexibank import metadata
from pylexibank import forms
from pylexibank import report
from pylexibank.profile import Profile
from pylexibank.util import ENTRY_POINT
from pylexibank.lingpy_util import settings

__all__ = ['Dataset']
assert ENTRY_POINT  # ENTRY_POINT used to be imported from here.


class TokenizerType(Protocol):  # pylint: disable=R0903,C0115
    def __call__(self, item: dict, string: str, **kw) -> list[str]:
        ...  # pragma: no cover


class Dataset(BaseDataset):  # pylint: disable=R0902
    """
    A lexibank dataset.

    This object provides access to a dataset's
    - language list as attribute `languages`
    - concept list as attribute `concepts`
    - concepticon concept-list ID as attribute `conceptlist`
    """
    metadata_cls = metadata.LexibankMetadata
    # The CLDFWriter can be instructed to keep only objects which are referenced from FormTable by
    # setting the following options to `False`.
    writer_options = {'keep_languages': True, 'keep_parameters': True}

    lexeme_class = models.Lexeme
    cognate_class = models.Cognate
    language_class = models.Language
    concept_class = models.Concept

    form_spec = forms.FormSpec()

    # If a dataset provides cross-concept cognate sets, it must declare this by setting the below
    # flag to True.
    cross_concept_cognates = False

    def __init__(self, concepticon=None, glottolog=None):
        super().__init__()
        if self.__class__ != Dataset:
            if not self.id:
                raise ValueError(
                    f"Dataset.id needs to be specified in subclass for {self.__class__}!")
        self.unmapped = Unmapped()
        self._json = self.dir / 'lexibank.json'
        self.contributors_path: pathlib.Path = self.dir / 'CONTRIBUTORS.md'

        self.conceptlists: list[Conceptlist] = []
        self.glottolog = glottolog
        self.concepticon = concepticon
        self.tr: Optional[transcription.Report] = None

    def cldf_specs(self) -> CLDFSpec:
        """Specification of the CLDF dataset."""
        return CLDFSpec(
            module='Wordlist',
            writer_cls=cldf.LexibankWriter,
            dir=self.cldf_dir,
            metadata_fname=cldf.MD_NAME,
            default_metadata_path=pathlib.Path(__file__).parent / cldf.MD_NAME)

    def _iter_etc(self, what):
        delimiter = '\t'
        path = self.etc_dir / (what + '.tsv')
        if not path.exists():
            delimiter = ','
            path = path.parent / (what + '.csv')
        return reader(path, dicts=True, delimiter=delimiter) if path.exists() else []

    def read_json(self):  # pragma: no cover
        """Read an object from a JSON file."""
        return jsonlib.load(self._json) if self._json.exists() else {}

    def write_json(self, obj):  # pragma: no cover
        """Write an object serialized as JSON to a file."""
        jsondump(obj, self._json)

    def get_creators_and_contributors(self, strict: bool = False) -> tuple[list, list]:
        """Get lists of dataset collaborators."""
        if self.contributors_path.exists():
            return metadata.get_creators_and_contributors(self.contributors_path, strict=strict)
        return [], []

    @functools.cached_property
    def sources(self) -> list[dict]:
        """Rows of etc/sources.csv"""
        return list(self._iter_etc('sources'))

    @functools.cached_property
    def concepts(self) -> list[dict]:
        """Rows of etc/concepts.csv"""
        return list(self._iter_etc('concepts'))

    @functools.cached_property
    def languages(self) -> list[dict]:
        """Rows of etc/languages.csv"""
        res = []
        for item in self._iter_etc('languages'):
            if item.get('GLOTTOCODE', None) and not \
                    Glottocode.pattern.match(item['GLOTTOCODE']):  # pragma: no cover
                raise ValueError(f"Invalid glottocode {item['GLOTTOCODE']}")
            res.append(item)
        return res

    def _replacements(self, what, source_col, target_col='REPLACEMENT'):
        return collections.OrderedDict(
            [(item[source_col], item[target_col]) for item in self._iter_etc(what)])

    @functools.cached_property
    def lexemes(self) -> collections.OrderedDict[str, str]:
        """Lexemes marked for replacement."""
        return self._replacements('lexemes', 'LEXEME')

    @functools.cached_property
    def segments(self) -> collections.OrderedDict[str, str]:
        """Segments marked for replacement."""
        return self._replacements('segments', 'SEGMENT')

    # ---------------------------------------------------------------
    # handling of lexemes/forms/words
    # ---------------------------------------------------------------
    @functools.cached_property
    def orthography_profile_dict(self) -> dict[Union[None, str], Profile]:
        """A dict of orthography profiles."""
        res = {}
        profile = self.etc_dir / 'orthography.tsv'
        profile_dir = self.etc_dir / 'orthography'
        if profile.exists():
            res[None] = profile
        if profile_dir.exists() and profile_dir.is_dir():
            for p in profile_dir.glob('*.tsv'):
                res[p.stem] = p

        return {k: Profile.from_file(str(p), form='NFC') for k, p in res.items()}

    @staticmethod
    def form_for_segmentation(form: str) -> str:
        """Normalized form to be segmented."""
        return unicodedata.normalize('NFC', '^' + form + '$')

    @functools.cached_property
    def tokenizer(self) -> Optional[TokenizerType]:
        """
        Datasets can provide support for segmentation (aka tokenization) in two ways:
        - by providing an orthography profile at etc/orthography.tsv or
        - by overwriting this method to return a custom tokenizer callable.

        :return: A callable to do segmentation.

        The expected signature of the callable is

            def t(item, string, **kw)

        where
        - `item` is a `dict` representing the complete CLDF FormTable row
        - `string` is the string to be segmented
        - `kw` may be used to pass any context info to the tokenizer, when called
          explicitly.
        """
        tokenizers = {
            k: Tokenizer(profile=p, errors_replace=lambda c: f'<{c}>')  # pylint: disable=W0108
            for k, p in self.orthography_profile_dict.items()}

        if tokenizers:
            def _tokenizer(item, string, **kw):
                """
                Adds `Profile` and `Graphemes` keys to `item`, returns `list` of segments.
                """
                kw.setdefault("column", "IPA")
                kw.setdefault("separator", " + ")
                profile = kw.pop('profile', None)
                if profile:
                    tokenizer = tokenizers[profile]
                    item['Profile'] = profile
                elif isinstance(item, dict) \
                        and 'Language_ID' in item \
                        and item['Language_ID'] in tokenizers:
                    tokenizer = tokenizers[item['Language_ID']]
                    item['Profile'] = item['Language_ID']
                else:
                    tokenizer = tokenizers[None]
                    item['Profile'] = 'default'
                form = self.form_for_segmentation(string)
                res = tokenizer(form, **kw).split()
                kw['column'] = Profile.GRAPHEME_COL
                item['Graphemes'] = tokenizer(form, **kw)
                return res
            return _tokenizer
        return None  # pragma: no cover

    @property
    def _transcription_report_path(self):
        return self.cldf_dir / '.transcription-report.json'

    def _cmd_makecldf(self, args):
        # Inject the appropriate CLDFWriter instance:
        self.unmapped.clear()
        self.tr = transcription.Report()

        if len(self.metadata.conceptlist):
            self.conceptlists = [
                self.concepticon.conceptlists[key] for key in self.metadata.conceptlist]

        if self.concept_class is models.CONCEPTICON_CONCEPTS:
            assert self.conceptlists
            self.concept_class = models.concepticon_concepts(self.conceptlists)

        # During _cmd_makecldf the transcription report will be updated.
        super()._cmd_makecldf(args)

        # make sure properties have the appropriate datatypes:
        ds = self.cldf_reader()
        for col in ds['LanguageTable'].tableSchema.columns:
            if col.name.lower() == 'population':  # pragma: no cover
                assert col.datatype.base == 'integer', 'population must be integer!'

        if args.verbose:
            self.unmapped.pprint()
        if not args.dev:
            assert self.cldf_reader().validate(args.log)

        # Compute summary stats for the updated transcription analyses.
        self.tr.compute_stats()

        # Aggregate transcription analysis results ...
        jsondump(self.tr.to_json(), self._transcription_report_path, log=args.log)

        # ... and write a report:
        self._cmd_readme(args)
        (self.dir / 'TRANSCRIPTION.md').write_text(str(self.tr), encoding='utf8')
        log_dump(self.dir / 'TRANSCRIPTION.md', args.log)

        jsondump(settings(), self.cldf_dir / 'lingpy-rcParams.json', log=args.log)

    def cmd_readme(self, args: argparse.Namespace) -> str:
        res = self.metadata.markdown()
        tr = self._transcription_report_path
        tr = jsonlib.load(tr) if tr.exists() else None
        res += report.report(
            self,
            tr,
            None if args.dev else getattr(args, 'glottolog', None),
            args.log,
        )
        if self.contributors_path.exists():
            res += f'\n\n{self.contributors_path.read_text(encoding="utf8")}\n\n'
        self.dir.write('FORMS.md', self.form_spec.as_markdown(self))
        return res


@dataclasses.dataclass
class Unmapped:
    """Functionality to keep track of unmapped objects."""
    languages: set[models.Language] = dataclasses.field(default_factory=set)
    concepts: set[models.Concept] = dataclasses.field(default_factory=set)

    def clear(self):  # pylint: disable=C0116
        self.languages = set()
        self.concepts = set()

    def add_concept(self, **kw):  # pylint: disable=C0116
        self.concepts.add(models.Concept(**kw))

    def add_language(self, **kw):  # pylint: disable=C0116
        self.languages.add(models.Language(**kw))

    @staticmethod
    def quote(v) -> str:
        """Quote a string."""
        v = f"{v or ''}"
        if ',' in v or len(v.split()) > 1:
            v = '"%s"' % v.replace('"', '""')  # pylint: disable=C0209
        return v

    def pprint(self):
        """Pretty print unmapped objects."""
        for objs, cls in [(self.languages, models.Language), (self.concepts, models.Concept)]:
            if objs:
                print(f'=== Unmapped {cls.__name__}s ===')
                print(','.join([a.name.upper() for a in dataclasses.fields(cls)]))
                for row in sorted(map(dataclasses.astuple, objs)):
                    print(','.join(map(self.quote, row)))
