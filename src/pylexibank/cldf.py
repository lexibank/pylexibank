# coding: utf8
from __future__ import unicode_literals, print_function, division

import attr
from csvw.metadata import Column
from clldutils.path import copy, Path
from clldutils.misc import slug
from pycldf.dataset import Wordlist


class Dataset(object):
    def __init__(self, dataset):
        self._count = 0
        self._cognate_count = 0
        self.dataset = dataset

        md = self.dataset.cldf_dir.joinpath('cldf-metadata.json')
        if not md.exists():
            copy(Path(__file__).parent / 'cldf-metadata.json', md)
        self.wl = Wordlist.from_metadata(md)

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
            for field in cls.fieldnames():
                if field not in cols:
                    self.wl[cls.__cldf_table__()].tableSchema.columns.append(
                        Column(name=field, datatype="string"))

    def validate(self, log=None):
        return self.wl.validate(log)

    def __getitem__(self, type_):
        return self.wl[type_]

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        for table in ['FormTable', 'CognateTable', 'LanguageTable', 'ParameterTable']:
            self.objects.setdefault(table, [])
        self.write(**self.objects)

    def add_sources(self, *args):
        self.wl.sources.add(*args)

    def lexeme_id(self):
        self._count += 1
        return '{0}'.format(self._count)

    def cognate_id(self):
        self._cognate_count += 1
        return self._cognate_count

    def add_lexemes(self, **kw):
        """
        :return: list of dicts corresponding to newly created Lexemes
        """
        lexemes = []
        for i, form in enumerate(self.dataset.split_forms(kw, kw['Value'])):
            kw_ = kw.copy()
            if form:
                if form != kw_['Value']:
                    self.dataset.log.debug(
                        'iter_forms split: "{0}" -> "{1}"'.format(kw_['Value'], form))
                _form = self.dataset.clean_form(kw_, form)
                if _form != form:
                    self.dataset.log.debug(
                        'clean_form changed: "{0}" -> "{1}"'.format(form, _form))
                form = _form.strip()
                if form:
                    kw_.setdefault('Segments', self.dataset._segment(kw_, form) or [])
                    kw_.update(ID=self.lexeme_id(), Form=form)
                    lexemes.append(self._add_object(self.dataset.lexeme_class, **kw_))

        return lexemes

    def _add_object(self, cls, **kw):
        # Instantiating an object will trigger potential validators:
        d = attr.asdict(cls(**kw))
        for key in ['ID', 'Language_ID', 'Parameter_ID', 'Cognateset_ID']:
            # We prefix IDs to make them lexibank-wide unique:
            if d.get(key):
                d[key] = '{0}-{1}'.format(self.dataset.id, slug('{0}'.format(d[key])))
        if 'ID' not in d or d['ID'] not in self._obj_index[cls.__cldf_table__()]:
            if 'ID' in d:
                self._obj_index[cls.__cldf_table__()].add(d['ID'])
            self.objects[cls.__cldf_table__()].append(d)
        return d

    def add_cognate(self, lexeme=None, **kw):
        if lexeme:
            kw.setdefault('Word_ID', lexeme['ID'])
            kw.setdefault('Form', lexeme['Form'])
        kw.setdefault('Index', self.cognate_id())
        return self._add_object(self.dataset.cognate_class, **kw)

    def add_language(self, **kw):
        return self._add_object(self.dataset.language_class, **kw)

    def add_concept(self, **kw):
        return self._add_object(self.dataset.concept_class, **kw)

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
        self.wl._tg.notes.append({
            'dc:title': 'environment',
            'properties': {
                'concepticon_version': self.dataset.concepticon.version,
                'glottolog_version': self.dataset.glottolog.version,
            }
        })
        self.wl.write(**kw)
