# coding: utf8
from __future__ import unicode_literals, print_function, division

from clldutils.path import Path

from pylexibank.dataset import Dataset


class Test(Dataset):
    dir = Path(__file__).parent

    def get_tokenizer(self):
        from pylexibank.lingpy_util import segmentize
        return lambda _, s: segmentize(s)

    def cmd_download(self, **kw):
        pass

    def cmd_install(self, **kw):
        from pylexibank.lingpy_util import iter_cognates
        self.raw.read_bib()
        with self.cldf as ds:
            ds.add_sources('@book{abc,\ntitle={The Title}\n}')
            ds.add_language(ID='lang1')
            ds.add_language(ID='lang2')
            ds.add_concept(ID='param1')
            ds.add_concept(ID='param2')
            for l in ds.add_lexemes(
                Language_ID='lang1',
                Parameter_ID='param1',
                Value='a b; c'
            ):
                ds.add_cognate(lexeme=l, Cognateset_ID='c-1')
            ds.add_lexemes(
                Language_ID='lang2',
                Parameter_ID='param2',
                Value='a~b')
            list(iter_cognates(ds))
