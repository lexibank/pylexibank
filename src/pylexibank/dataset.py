# coding: utf8
from __future__ import unicode_literals, print_function, division
import logging
from datetime import datetime
import re
import pkg_resources

import attr
import six
import git
from clldutils.dsv import reader
from clldutils.text import split_text_with_context, strip_brackets
from clldutils.misc import lazyproperty
from clldutils.loglib import Logging
from clldutils.path import remove, rmtree, write_text
from clldutils import licenses
from clldutils import jsonlib
from pyglottolog.languoids import Glottocode

from lingpy.settings import rc
from segments.tokenizer import Tokenizer

import pylexibank
from pylexibank.util import DataDir, jsondump
from pylexibank import cldf

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
        convert=lambda v: [v] if isinstance(v, six.string_types) else v)
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
        default=False, convert=lambda v: v if isinstance(v, bool) else eval(v))
    Cognate_Detection_Method = attr.ib(default='expert')
    Source = attr.ib(
        default=attr.Factory(list),
        validator=attr.validators.instance_of(list),
        convert=lambda v: [v] if isinstance(v, six.string_types) else v)
    Alignment = attr.ib(
        default=None, convert=lambda v: ' '.join(v) if isinstance(v, list) else v)
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
    conceptlist = attr.ib(default=None)
    lingpy_schema = attr.ib(default=None)
    derived_from = attr.ib(default=None)
    related = attr.ib(default=None)
    source = attr.ib(default=None)

    @property
    def common_props(self):
        return {
            "dc:title": self.title,
            "dc:description": self.description,
            "dc:bibliographicCitation": self.citation,
            "dc:license": licenses.find(self.license) if self.license else None,
            "dc:identifier": self.url,
            "dc:format": "http://concepticon.clld.org/contributions/{0}".format(
                self.conceptlist) if self.conceptlist else None,
            "dc:isVersionOf": "http://lexibank.clld.org/contributions/{0}".format(
                self.derived_from) if self.derived_from else None,
            "dc:related": self.related,
            "aboutUrl": self.aboutUrl,
        }


class Dataset(object):
    """
    A lexibank dataset.

    This object provides access to a dataset's
    - language list as attribute `languages`
    - concept list as attribute `concepts`
    - concepticon concept-list ID as attribute `conceptlist`
    """
    dir = None  # Derived classes must provide an existing directory here!
    lexeme_class = Lexeme
    cognate_class = Cognate
    language_class = Language
    concept_class = Concept
    log = logging.getLogger(pylexibank.__name__)

    @lazyproperty
    def id(self):
        return self.dir.name

    @lazyproperty
    def metadata(self):
        return Metadata(**jsonlib.load(self.dir / 'metadata.json'))

    @property
    def stats(self):
        if self.dir.joinpath('README.json').exists():
            return jsonlib.load(self.dir / 'README.json')
        return {}

    def __init__(self, concepticon=None, glottolog=None):
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

    def _iter_etc(self, what):
        path = self.dir / 'etc' / what
        return reader(path, dicts=True) if path.exists() else []

    def read_json(self):
        return jsonlib.load(self._json) if self._json.exists() else {}

    def write_json(self, obj):
        jsondump(obj, self._json)

    @lazyproperty
    def github_repo(self):  # pragma: no cover
        try:
            match = re.search(
                'github\.com/(?P<org>[^/]+)/%s\.git' % re.escape(self.id),
                self.git_repo.remotes.origin.url)
            if match:
                return match.group('org') + '/' + self.id
        except AttributeError:
            pass

    @lazyproperty
    def sources(self):
        return list(self._iter_etc('sources.csv'))

    @lazyproperty
    def concepts(self):
        return list(self._iter_etc('concepts.csv'))

    @lazyproperty
    def languages(self):
        res = []
        for item in self._iter_etc('languages.csv'):
            if item.get('GLOTTOCODE', None) and not \
                    Glottocode.pattern.match(item['GLOTTOCODE']):  # pragma: no cover
                raise ValueError(
                    "Wrong glottocode for item {0}".format(item['GLOTTOCODE']))
            res.append(item)
        return res

    @lazyproperty
    def lexemes(self):
        res = {}
        for item in self._iter_etc('lexemes.csv'):
            res[item['LEXEME']] = item['REPLACEMENT']
        return res

    def debug(self):
        return Logging(self.log)

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
    def clean_form(self, item, form):
        """
        Called when a row is added to a CLDF dataset.

        :param form:
        :return: None to skip the form, or the cleaned form as string.
        """
        form = strip_brackets(form)
        if form not in ['?']:
            return form

    def split_forms(self, item, value):
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
            obj = Tokenizer(profile=str(profile))

            def _tokenizer(item, string, **kw):
                kw.setdefault("column", "IPA")
                kw.setdefault("separator", " _ ")
                return obj(string, **kw).split()
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
        self.unmapped.clear()
        rmtree(self.cldf_dir)
        self.cldf_dir.mkdir()

        if self.metadata.conceptlist:
            self.conceptlist = self.concepticon.conceptlists[self.metadata.conceptlist]
        rc(schema=self.metadata.lingpy_schema or 'ipa')
        if self.cmd_install(**kw) != NOOP:
            if kw.get('verbose'):
                self.unmapped.pprint()
            self.cldf.validate(kw['log'])

    def _clean(self, **kw):
        self.log.debug('removing CLDF directory %s' % self.cldf_dir)
        if self.cldf_dir.exists():
            for f in self.cldf_dir.iterdir():
                if f.is_file():
                    remove(f)
                else:
                    rmtree(f)

    def _not_implemented(self, method):
        self.log.warn('cmd_{0} not implemented for dataset {1}'.format(method, self.id))

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
            if verbose:
                print('Importing {0} failed: {1}'.format(ep.name, e))
