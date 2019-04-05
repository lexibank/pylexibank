import logging
from datetime import datetime
import re
import pkg_resources
from collections import Counter, defaultdict
import unicodedata

import attr
import git
from clldutils.dsv import reader
from clldutils.text import split_text_with_context
from clldutils.misc import lazyproperty
from clldutils.path import remove, rmtree, write_text
from clldutils import licenses
from clldutils import jsonlib
from pyglottolog.languoids import Glottocode

from segments import Tokenizer, Profile
from segments.tree import Tree

import pylexibank
from pylexibank.util import DataDir, jsondump, textdump, get_badge
from pylexibank import cldf
from pylexibank import transcription

NOOP = -1


def non_empty(_, attribute, value):
    if not value:
        raise ValueError('{0} must be non-empty'.format(attribute))


class FieldnamesMixin(object):
    @classmethod
    def fieldnames(cls):
        return [f.name for f in attr.fields(cls)]


@attr.s(hash=False)
class Language(FieldnamesMixin):
    ID = attr.ib(default='', hash=True)
    Name = attr.ib(default=None)
    ISO639P3code = attr.ib(default=None)
    Glottocode = attr.ib(default=None)
    Macroarea = attr.ib(default=None)

    Glottolog_Name = attr.ib(default=None)
    Family = attr.ib(default=None)

    @classmethod
    def __cldf_table__(cls):
        return 'LanguageTable'


@attr.s(hash=False)
class Concept(FieldnamesMixin):
    ID = attr.ib(default='', hash=True)
    Name = attr.ib(default='')
    Concepticon_ID = attr.ib(default=None)
    Concepticon_Gloss = attr.ib(default=None)

    @classmethod
    def __cldf_table__(cls):
        return 'ParameterTable'


@attr.s
class Lexeme(FieldnamesMixin):
    """
    Raw lexical data item as it can be pulled out of the original datasets.

    This is the basis for creating rows in CLDF representations of the data by
    - splitting the lexical item into forms
    - cleaning the forms
    - potentially tokenizing the form
    """
    ID = attr.ib()
    Form = attr.ib()
    Value = attr.ib(validator=non_empty)  # the lexical item
    Language_ID = attr.ib(validator=non_empty)
    Parameter_ID = attr.ib(validator=non_empty)
    Local_ID = attr.ib(default=None)  # local ID of a lexeme in the source dataset
    Segments = attr.ib(
        default=attr.Factory(list),
        validator=attr.validators.instance_of(list))
    Source = attr.ib(
        default=attr.Factory(list),
        validator=attr.validators.instance_of(list),
        converter=lambda v: [v] if isinstance(v, str) else v)
    Comment = attr.ib(default=None)
    Cognacy = attr.ib(default=None)
    Loan = attr.ib(
        default=None,
        validator=attr.validators.optional(attr.validators.instance_of(bool)))

    @classmethod
    def __cldf_table__(cls):
        return 'FormTable'


@attr.s
class Cognate(FieldnamesMixin):
    ID = attr.ib(default=None)
    Form_ID = attr.ib(default=None)
    Form = attr.ib(default=None)
    Cognateset_ID = attr.ib(default=None)
    Doubt = attr.ib(
        default=False,
        converter=lambda v: v if isinstance(v, bool) else eval(v))
    Cognate_Detection_Method = attr.ib(default='expert')
    Source = attr.ib(
        default=attr.Factory(list),
        validator=attr.validators.instance_of(list),
        converter=lambda v: [v] if isinstance(v, str) else v)
    Alignment = attr.ib(
        default=None,
        converter=lambda v: v if isinstance(v, list) or v is None else v.split())
    Alignment_Method = attr.ib(default=None)
    Alignment_Source = attr.ib(default=None)

    @classmethod
    def __cldf_table__(cls):
        return 'CognateTable'


@attr.s
class Metadata(object):
    title = attr.ib(default=None)
    description = attr.ib(default=None)
    citation = attr.ib(default=None)
    license = attr.ib(default=None)
    url = attr.ib(default=None)
    aboutUrl = attr.ib(default=None)
    conceptlist = attr.ib(
        default=[],
        converter=lambda s: [] if not s else (s if isinstance(s, list) else [s]))
    lingpy_schema = attr.ib(default=None)
    derived_from = attr.ib(default=None)
    related = attr.ib(default=None)
    source = attr.ib(default=None)

    @lazyproperty
    def known_license(self):
        if self.license:
            return licenses.find(self.license)

    @property
    def common_props(self):
        res = {
            "dc:title": self.title,
            "dc:description": self.description,
            "dc:bibliographicCitation": self.citation,
            "dc:license": licenses.find(self.license or ''),
            "dc:identifier": self.url,
            "dc:format": [
                "http://concepticon.clld.org/contributions/{0}".format(cl)
                for cl in self.conceptlist],
            "dc:isVersionOf": "http://lexibank.clld.org/contributions/{0}".format(
                self.derived_from) if self.derived_from else None,
            "dc:related": self.related,
            "aboutUrl": self.aboutUrl,
        }
        if self.known_license:
            res['dc:license'] = self.known_license.url
        elif self.license:
            res['dc:license'] = self.license

        return res


class Dataset(object):
    """
    A lexibank dataset.

    This object provides access to a dataset's
    - language list as attribute `languages`
    - concept list as attribute `concepts`
    - concepticon concept-list ID as attribute `conceptlist`
    """
    dir = None  # Derived classes must provide an existing directory here!
    id = None  # Derived classes must provide a unique ID here!
    lexeme_class = Lexeme
    cognate_class = Cognate
    language_class = Language
    concept_class = Concept
    log = logging.getLogger(pylexibank.__name__)

    @lazyproperty
    def metadata(self):
        return Metadata(**jsonlib.load(self.dir / 'metadata.json'))

    @property
    def stats(self):
        if self.dir.joinpath('README.json').exists():
            return jsonlib.load(self.dir / 'README.json')
        return {}

    def __init__(self, concepticon=None, glottolog=None):
        if self.__class__ != Dataset:
            if not self.dir:
                raise ValueError(
                    "Dataset.dir needs to be specified in subclass for %s!" % self.__class__)
            elif not self.id:
                raise ValueError(
                    "Dataset.id needs to be specified in subclass for %s!" % self.__class__)
        self.unmapped = Unmapped()
        self.dir = DataDir(self.dir)
        self._json = self.dir.joinpath('lexibank.json')
        self.raw = DataDir(self.dir / 'raw')
        self.raw.mkdir(exist_ok=True)
        self.cldf_dir = self.dir / 'cldf'
        self.cldf_dir.mkdir(exist_ok=True)

        self.conceptlist = {}
        self.glottolog = glottolog
        self.concepticon = concepticon
        try:
            self.git_repo = git.Repo(str(self.dir))  # pragma: no cover
        except git.InvalidGitRepositoryError:
            self.git_repo = None
        self.tr_analyses = {}
        self.tr_bad_words = []
        self.tr_invalid_words = []

    def _iter_etc(self, what):
        delimiter = '\t'
        path = self.dir / 'etc' / (what + '.tsv')
        if not path.exists():
            delimiter = ','
            path = path.parent / (what + '.csv')
        return reader(path, dicts=True, delimiter=delimiter) if path.exists() else []

    def read_json(self):  # pragma: no cover
        return jsonlib.load(self._json) if self._json.exists() else {}

    def write_json(self, obj):  # pragma: no cover
        jsondump(obj, self._json)

    @lazyproperty
    def github_repo(self):  # pragma: no cover
        try:
            match = re.search(
                'github\.com/(?P<org>[^/]+)/(?P<repo>[^.]+)\.git',
                self.git_repo.remotes.origin.url)
            if match:
                return match.group('org') + '/' + match.group('repo')
        except AttributeError:
            pass

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

    @lazyproperty
    def lexemes(self):
        res = {}
        for item in self._iter_etc('lexemes'):
            res[item['LEXEME']] = item['REPLACEMENT']
        return res

    # ---------------------------------------------------------------
    # workflow actions whih should be overwritten by derived classes:
    # ---------------------------------------------------------------
    def cmd_download(self, **kw):
        self._not_implemented('download')
        return NOOP

    def cmd_install(self, **kw):
        self._not_implemented('install')
        return NOOP

    # ---------------------------------------------------------------
    # handling of lexemes/forms/words
    # ---------------------------------------------------------------
    def iter_raw_lexemes(self):
        """
        Datasets should overwrite this method, yielding raw lexical items, if seeding
        an orthography profile via `lexibank orthography`.
        """
        yield "abcde"

    def clean_form(self, item, form):
        """
        Called when a row is added to a CLDF dataset.

        :param form:
        :return: None to skip the form, or the cleaned form as string.
        """
        if form not in ['?']:
            return form

    def split_forms(self, item, value):
        if value in self.lexemes:  # pragma: no cover
            self.log.debug('overriding via lexemes.csv: %r -> %r' % (value, self.lexemes[value]))
        value = self.lexemes.get(value, value)
        return [self.clean_form(item, form)
                for form in split_text_with_context(value, separators='/,;')]

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
        profile = self.dir / 'etc' / 'orthography.tsv'
        if profile.exists():
            profile = Profile.from_file(str(profile), form='NFC')
            default_spec = list(next(iter(profile.graphemes.values())).keys())
            for grapheme in ['^', '$']:
                if grapheme not in profile.graphemes:
                    profile.graphemes[grapheme] = {k: None for k in default_spec}
            profile.tree = Tree(list(profile.graphemes.keys()))
            tokenizer = Tokenizer(profile=profile, errors_replace=lambda c: '<{0}>'.format(c))

            def _tokenizer(item, string, **kw):
                kw.setdefault("column", "IPA")
                kw.setdefault("separator", " + ")
                return tokenizer(unicodedata.normalize('NFC', '^' + string + '$'), **kw).split()
            return _tokenizer

    # ---------------------------------------------------------------
    # CLDF dataset access
    # ---------------------------------------------------------------
    @lazyproperty
    def cldf(self):
        return cldf.Dataset(self)

    # ---------------------------------------------------------------
    def _download(self, **kw):
        self.cmd_download(**kw)
        write_text(
            self.raw / 'README.md',
            'Raw data downloaded {0}'.format(datetime.utcnow().isoformat()))

    def _install(self, **kw):
        self.log = kw.get('log', self.log)
        self.unmapped.clear()
        for p in self.cldf_dir.iterdir():
            if p.name not in ['README.md', '.gitattributes']:
                p.unlink()
        self.tr_analyses = {}
        self.tr_bad_words = []
        self.tr_invalid_words = []

        if len(self.metadata.conceptlist):
            self.conceptlist = self.concepticon.conceptlists[self.metadata.conceptlist[0]]
        if self.cmd_install(**kw) == NOOP:
            return

        if self.metadata.known_license:
            legalcode = self.metadata.known_license.legalcode
            if legalcode:
                write_text(self.dir / 'LICENSE', legalcode)

        gitattributes = self.cldf_dir / '.gitattributes'
        if not gitattributes.exists():
            with gitattributes.open('wt') as fp:
                fp.write('*.csv text eol=crlf')

        if kw.get('verbose'):
            self.unmapped.pprint()
        self.cldf.validate(kw['log'])

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
        # ... and write a report:
        for text, fname in [
            (transcription.report(tr), 'TRANSCRIPTION.md'),
            (self.report(tr, log=kw.get('log')), 'README.md'),
        ]:
            textdump(text, self.dir / fname, log=kw.get('log'))

    def _clean(self, **kw):
        self.log.debug('removing CLDF directory %s' % self.cldf_dir)
        if self.cldf_dir.exists():
            for f in self.cldf_dir.iterdir():
                if f.is_file():
                    remove(f)
                else:
                    rmtree(f)

    def _not_implemented(self, method):
        self.log.warning('cmd_{0} not implemented for dataset {1}'.format(method, self.id))

    def coverage(self, vars, glangs, c):  # pragma: no cover
        for row in self.cldf['FormTable']:
            try:
                cid = int(row['Parameter_ID'])
            except (ValueError, TypeError):
                continue
            vid = self.id + '-' + row['Language_ID']
            c[cid].add(vid)
            vars[vid].add(cid)
            glangs[row['Language_ID']].add(cid)

    def build_status_badge(self):
        if not self.dir.joinpath('.travis.yml').exists():
            return ''
        try:
            return "[![Build Status](https://travis-ci.org/{0}.svg?branch=master)]" \
                   "(https://travis-ci.org/{0})".format(self.github_repo)
        except:  # noqa
            return ''

    def report(self, tr_analysis, log=None):
        #
        # FIXME: write only summary into README.md
        # in case of multiple cldf datasets:
        # - separate lexemes.md and transcriptions.md
        #
        if not list(self.cldf_dir.glob('*.csv')):
            return
        lines = [
            '# %s\n' % self.metadata.title,
            'Cite the source dataset as\n',
            '> %s\n' % self.metadata.citation,
        ]

        if self.metadata.license:
            lines.extend([
                'This dataset is licensed under a %s license' % self.metadata.license, ''])

        if self.metadata.url:
            lines.extend(['Available online at %s' % self.metadata.url, ''])

        if self.metadata.related:
            lines.extend(['See also %s' % self.metadata.related, ''])

        if self.metadata.conceptlist:
            lines.append('Conceptlists in Concepticon:')
            lines.extend([
                '- [{0}](http://concepticon.clld.org/contributions/{0})'.format(cl)
                for cl in self.metadata.conceptlist])
            lines.append('')

        # add NOTES.md
        if self.dir.joinpath('NOTES.md').exists():
            lines.extend(['## Notes', ''])
            lines.extend(self.dir.joinpath('NOTES.md').read_text().split("\n"))
            lines.extend(['', ''])  # some blank lines

        synonyms = defaultdict(Counter)
        totals = {
            'languages': Counter(),
            'concepts': Counter(),
            'sources': Counter(),
            'cognate_sets': Counter(),
            'lexemes': 0,
            'lids': Counter(),
            'cids': Counter(),
        }

        missing_source = []
        missing_lang = []

        param2concepticon = {r['ID']: r['Concepticon_ID'] for r in self.cldf['ParameterTable']}
        lang2glottolog = {r['ID']: r['Glottocode'] for r in self.cldf['LanguageTable']}

        for row in self.cldf['FormTable']:
            if row['Source']:
                totals['sources'].update(['y'])
            else:
                missing_source.append(row)
            totals['concepts'].update([param2concepticon[row['Parameter_ID']]])
            totals['languages'].update([lang2glottolog[row['Language_ID']]])
            totals['lexemes'] += 1
            totals['lids'].update([row['Language_ID']])
            totals['cids'].update([row['Parameter_ID']])
            synonyms[row['Language_ID']].update([row['Parameter_ID']])

        for row in self.cldf['CognateTable']:
            totals['cognate_sets'].update([row['Cognateset_ID']])

        sindex = sum(
            [sum(list(counts.values())) / float(len(counts)) for counts in synonyms.values()])
        langs = set(synonyms.keys())
        if langs:
            sindex /= float(len(langs))
        else:
            sindex = 0
        totals['SI'] = sindex

        stats = tr_analysis['stats']
        lsegments = len(stats['segments'])
        lbipapyerr = len(stats['bipa_errors'])
        lsclasserr = len(stats['sclass_errors'])

        def ratio(prop):
            if float(totals['lexemes']) == 0:
                return 0
            return sum(v for k, v in totals[prop].items() if k) / float(totals['lexemes'])

        num_cognates = sum(1 for k, v in totals['cognate_sets'].items())
        # see List et al. 2017
        # diff between cognate sets and meanings / diff between words and meanings
        cog_diversity = (num_cognates - len(totals['cids'])) \
            / (totals['lexemes'] - len(totals['cids']))

        badges = [
            self.build_status_badge(),
            get_badge(ratio('languages'), 'Glottolog'),
            get_badge(ratio('concepts'), 'Concepticon'),
            get_badge(ratio('sources'), 'Source'),
        ]
        if lsegments:
            badges.extend([
                get_badge((lsegments - lbipapyerr) / lsegments, 'BIPA'),
                get_badge((lsegments - lsclasserr) / lsegments, 'CLTS SoundClass'),
            ])
        lines.extend(['## Statistics', '\n', '\n'.join(badges), ''])
        stats_lines = [
            '- **Varieties:** {0:,}'.format(len(totals['lids'])),
            '- **Concepts:** {0:,}'.format(len(totals['cids'])),
            '- **Lexemes:** {0:,}'.format(totals['lexemes']),
            '- **Synonymy:** {:0.2f}'.format(totals['SI']),
            '- **Cognacy:** {0:,} cognates in {1:,} cognate sets ({2:,} singletons)'.format(
                sum(v for k, v in totals['cognate_sets'].items()),
                num_cognates,
                len([k for k, v in totals['cognate_sets'].items() if v == 1])),
            '- **Cognate Diversity:** {:0.2f}'.format(cog_diversity),
            '- **Invalid lexemes:** {0:,}'.format(stats['invalid_words_count']),
            '- **Tokens:** {0:,}'.format(sum(stats['segments'].values())),
            '- **Segments:** {0:,} ({1} BIPA errors, {2} CTLS sound class errors, '
            '{3} CLTS modified)'
            .format(lsegments, lbipapyerr, lsclasserr, len(stats['replacements'])),
            '- **Inventory size (avg):** {:0.2f}'.format(stats['inventory_size']),
        ]
        if log:
            log.info('\n'.join(['Summary for dataset {}'.format(self.id)] + stats_lines))
        lines.extend(stats_lines)

        totals['languages'] = len(totals['lids'])
        totals['concepts'] = len(totals['cids'])
        totals['cognate_sets'] = bool(1 for k, v in totals['cognate_sets'].items() if v > 1)
        totals['sources'] = totals['sources'].get('y', 0)

        bookkeeping_languoids = []
        for lang in self.cldf['LanguageTable']:
            gl_lang = self.glottolog.cached_languoids.get(lang.get('Glottocode'))
            if gl_lang and gl_lang.category == 'Bookkeeping':
                bookkeeping_languoids.append(lang)

        # improvements section
        if missing_lang or missing_source or bookkeeping_languoids:
            lines.extend(['\n## Possible Improvements:\n', ])

            if missing_lang:
                lines.append("- Languages missing glottocodes: %d/%d (%.2f%%)" % (
                    len(missing_lang),
                    totals['languages'],
                    (len(missing_lang) / totals['languages']) * 100
                ))

            if bookkeeping_languoids:
                lines.append(
                    "- Languages linked to [bookkeeping languoids in Glottolog]"
                    "(http://glottolog.org/glottolog/glottologinformation"
                    "#bookkeepinglanguoids):")
            for lang in bookkeeping_languoids:
                lines.append(
                    '  - {0} [{1}](http://glottolog.org/resource/languoid/id/{1})'.format(
                        lang.get('Name', lang.get('ID')), lang['Glottocode']))
            lines.append('\n')

        if missing_source:
            lines.append("- Entries missing sources: %d/%d (%.2f%%)" % (
                len(missing_source),
                totals['lexemes'],
                (len(missing_source) / totals['lexemes']) * 100
            ))

        return lines


class NonSplittingDataset(Dataset):
    def split_forms(self, item, value):
        return [self.clean_form(item, self.lexemes.get(value, value))]


MARKDOWN_TEMPLATE = """
## Transcription Report

### General Statistics

* Number of Tokens: {tokens}
* Number of Segments: {segments}
* Invalid forms: {invalid}
* Inventory Size: {inventory_size:.2f}
* [Erroneous tokens](report.md#tokens): {general_errors}
* Erroneous words: {word_errors}
* Number of BIPA-Errors: {bipa_errors}
* Number of CLTS-SoundClass-Errors: {sclass_errors}
* Bad words: {words_errors}
"""


class Unmapped(object):
    def __init__(self):
        self.languages = set()
        self.concepts = set()

    def clear(self):
        self.languages = set()
        self.concepts = set()

    def add_concept(self, **kw):
        self.concepts.add(Concept(**kw))

    def add_language(self, **kw):
        self.languages.add(Language(**kw))

    @staticmethod
    def quote(v):
        v = '{0}'.format(v or '')
        if ',' in v or len(v.split()) > 1:
            v = '"%s"' % v.replace('"', '""')
        return v

    def pprint(self):
        for objs, cls in [(self.languages, Language), (self.concepts, Concept)]:
            if objs:
                print('=== Unmapped %ss ===' % cls.__name__)
                print(','.join([a.name.upper() for a in attr.fields(cls)]))
                for row in sorted(map(attr.astuple, objs)):
                    print(','.join(map(self.quote, row)))


def iter_datasets(glottolog=None, concepticon=None, verbose=False):
    for ep in pkg_resources.iter_entry_points('lexibank.dataset'):
        try:
            yield ep.load()(glottolog=glottolog, concepticon=concepticon)
        except ImportError as e:
            print('Importing {0} failed: {1}'.format(ep.name, e))
