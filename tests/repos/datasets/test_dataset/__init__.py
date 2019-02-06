# coding: utf8
from __future__ import unicode_literals, print_function, division

from clldutils.path import Path
from clldutils.misc import lazyproperty
import attr

from pylexibank.dataset import Dataset, Concept


@attr.s
class TestConcept(Concept):
    Chinese = attr.ib(default=None)


class Test(Dataset):
    dir = Path(__file__).parent
    id = 'test_dataset'
    concept_class = TestConcept
    github_repo = 'x/y'

    @lazyproperty
    def tokenizer(self):
        from lingpy.sequence.sound_classes import clean_string
        return lambda _, s: clean_string(s)

    def cmd_download(self, **kw):
        pass

    def cmd_install(self, **kw):
        from pylexibank.lingpy_util import iter_cognates
        self.raw.read_bib()
        with self.cldf as ds:
            ds.add_sources('@book{abc,\ntitle={The Title}\n}')
            ds.add_languages()
            ds.add_language(ID='lang1', Glottocode='abcd1234')
            ds.add_language(ID='lang2')
            ds.add_concepts()
            ds.add_concept(ID='param1', Concepticon_ID=1)
            ds.add_concept(ID='param2')
            for l in ds.add_lexemes(
                Language_ID='lang1',
                Parameter_ID='param1',
                Value='a b; c'
            ):
                ds.add_cognate(lexeme=l, Cognateset_ID='c-1')
            ds.add_lexemes(
                Language_ID='lang1',
                Parameter_ID='param1',
                Value='a^b',
                Source=['abc'],
            )
            ds.add_lexemes(
                Language_ID='lang1',
                Parameter_ID='param1',
                Value='^^^'
            )
            ds.add_lexemes(
                Language_ID='lang2',
                Parameter_ID='param2',
                Value='a~b')
            try:
                list(iter_cognates(ds))
            except ValueError:
                pass
            try:
                list(iter_cognates(ds, method='sca'))
            except ValueError:
                pass
