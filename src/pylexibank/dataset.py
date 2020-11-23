import pathlib
import collections
import unicodedata

import attr

from csvw.dsv import reader
from clldutils.misc import lazyproperty
from clldutils import jsonlib
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

__all__ = ['Dataset', 'ENTRY_POINT']
ENTRY_POINT = 'lexibank.dataset'


class Dataset(BaseDataset):
    """
    A lexibank dataset.

    This object provides access to a dataset's
    - language list as attribute `languages`
    - concept list as attribute `concepts`
    - concepticon concept-list ID as attribute `conceptlist`
    """
    metadata_cls = metadata.LexibankMetadata

    lexeme_class = models.Lexeme
    cognate_class = models.Cognate
    language_class = models.Language
    concept_class = models.Concept

    form_spec = forms.FormSpec()

    # If a dataset provides cross-concept cognate sets, it must declare this by setting the below
    # flag to True.
    cross_concept_cognates = False

    @property
    def stats(self):
        if self.dir.joinpath('README.json').exists():
            return jsonlib.load(self.dir / 'README.json')
        return {}

    def __init__(self, concepticon=None, glottolog=None):
        super().__init__()
        if self.__class__ != Dataset:
            if not self.id:
                raise ValueError(
                    "Dataset.id needs to be specified in subclass for %s!" % self.__class__)
        self.unmapped = Unmapped()
        self._json = self.dir / 'lexibank.json'
        self.contributors_path = self.dir / 'CONTRIBUTORS.md'

        self.conceptlists = []
        self.glottolog = glottolog
        self.concepticon = concepticon
        self.tr_analyses = {}
        self.tr_bad_words = []
        self.tr_invalid_words = []

    def cldf_specs(self):
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
        return jsonlib.load(self._json) if self._json.exists() else {}

    def write_json(self, obj):  # pragma: no cover
        jsondump(obj, self._json)

    def get_creators_and_contributors(self, strict=False):
        if self.contributors_path.exists():
            return metadata.get_creators_and_contributors(self.contributors_path, strict=strict)
        return [], []

    @lazyproperty
    def sources(self):
        return list(self._iter_etc('sources'))

    @lazyproperty
    def concepts(self):
        return list(self._iter_etc('concepts'))

    @lazyproperty
    def languages(self):
        res = []
        for item in self._iter_etc('languages'):
            if item.get('GLOTTOCODE', None) and not \
                    Glottocode.pattern.match(item['GLOTTOCODE']):  # pragma: no cover
                raise ValueError(
                    "Invalid glottocode {0}".format(item['GLOTTOCODE']))
            res.append(item)
        return res

    def _replacements(self, what, source_col, target_col='REPLACEMENT'):
        return collections.OrderedDict(
            [(item[source_col], item[target_col]) for item in self._iter_etc(what)])

    @lazyproperty
    def lexemes(self):
        return self._replacements('lexemes', 'LEXEME')

    @lazyproperty
    def segments(self):
        return self._replacements('segments', 'SEGMENT')

    # ---------------------------------------------------------------
    # handling of lexemes/forms/words
    # ---------------------------------------------------------------
    @lazyproperty
    def orthography_profile_dict(self):
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
    def form_for_segmentation(form):
        return unicodedata.normalize('NFC', '^' + form + '$')

    @lazyproperty
    def tokenizer(self):
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
            k: Tokenizer(profile=p, errors_replace=lambda c: '<{0}>'.format(c))
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

    def _cmd_makecldf(self, args):
        # Inject the appropriate CLDFWriter instance:
        self.unmapped.clear()
        self.tr_analyses = {}
        self.tr_bad_words = []
        self.tr_invalid_words = []

        if len(self.metadata.conceptlist):
            self.conceptlists = [
                self.concepticon.conceptlists[key] for key in self.metadata.conceptlist]

        if self.concept_class is models.CONCEPTICON_CONCEPTS:
            assert self.conceptlists
            self.concept_class = models.concepticon_concepts(self.conceptlists)

        super()._cmd_makecldf(args)

        #
        # make sure properties have the appropriate datatypes:
        #
        ds = self.cldf_reader()
        for col in ds['LanguageTable'].tableSchema.columns:
            if col.name.lower() == 'population':
                assert col.datatype.base == 'integer', 'population must be integer!'

        if args.verbose:
            self.unmapped.pprint()
        if not args.dev:
            assert self.cldf_reader().validate(args.log)

        stats = transcription.Stats(
            bad_words=sorted(self.tr_bad_words[:100], key=lambda x: x['ID']),
            bad_words_count=len(self.tr_bad_words),
            invalid_words=sorted(self.tr_invalid_words[:100], key=lambda x: x['ID']),
            invalid_words_count=len(self.tr_invalid_words))
        for lid, analysis in self.tr_analyses.items():
            for attribute in ['segments', 'bipa_errors', 'sclass_errors', 'replacements']:
                getattr(stats, attribute).update(getattr(analysis, attribute))
            stats.general_errors += analysis.general_errors
            stats.inventory_size += len(analysis.segments) / len(self.tr_analyses)

        error_segments = stats.bipa_errors.union(stats.sclass_errors)
        for i, row in enumerate(stats.bad_words):
            analyzed_segments = []
            for s in row['Segments']:
                analyzed_segments.append('<s> %s </s>' % s if s in error_segments else s)
            stats.bad_words[i] = [
                row['ID'],
                row['Language_ID'],
                row['Parameter_ID'],
                row['Form'],
                ' '.join(analyzed_segments)]

        for i, row in enumerate(stats.invalid_words):
            stats.invalid_words[i] = [
                row['ID'],
                row['Language_ID'],
                row['Parameter_ID'],
                row['Form']]
        # Aggregate transcription analysis results ...
        tr = dict(
            by_language={k: attr.asdict(v) for k, v in self.tr_analyses.items()},
            stats=attr.asdict(stats))

        jsondump(tr, self.cldf_dir / '.transcription-report.json', log=args.log)

        # ... and write a report:
        args.tr_analysis = tr
        self._cmd_readme(args)
        (self.dir / 'TRANSCRIPTION.md').write_text(transcription.report(tr), encoding='utf8')
        log_dump(self.dir / 'TRANSCRIPTION.md', args.log)

    def cmd_readme(self, args):
        res = self.metadata.markdown()
        tr = self.cldf_dir / '.transcription-report.json'
        tr = jsonlib.load(tr) if tr.exists() else None
        res += report.report(
            self,
            tr,
            None if args.dev else getattr(args, 'glottolog', None),
            args.log,
        )
        if self.contributors_path.exists():
            res += '\n\n{0}\n\n'.format(self.contributors_path.read_text(encoding='utf8'))
        self.dir.write('FORMS.md', self.form_spec.as_markdown(self))
        return res


class Unmapped(object):
    def __init__(self):
        self.languages = set()
        self.concepts = set()

    def clear(self):
        self.languages = set()
        self.concepts = set()

    def add_concept(self, **kw):
        self.concepts.add(models.Concept(**kw))

    def add_language(self, **kw):
        self.languages.add(models.Language(**kw))

    @staticmethod
    def quote(v):
        v = '{0}'.format(v or '')
        if ',' in v or len(v.split()) > 1:
            v = '"%s"' % v.replace('"', '""')
        return v

    def pprint(self):
        for objs, cls in [(self.languages, models.Language), (self.concepts, models.Concept)]:
            if objs:
                print('=== Unmapped %ss ===' % cls.__name__)
                print(','.join([a.name.upper() for a in attr.fields(cls)]))
                for row in sorted(map(attr.astuple, objs)):
                    print(','.join(map(self.quote, row)))
