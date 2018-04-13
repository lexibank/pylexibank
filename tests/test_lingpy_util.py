# coding: utf8
from __future__ import unicode_literals

import pytest
import attr
from lingpy import Wordlist

from pylexibank import lingpy_util
from pylexibank import dataset
from pylexibank.cldf import Dataset


def test_wordlist2cognates(repos, mocker):
    @attr.s
    class Lexeme(dataset.Lexeme):
        Concept = attr.ib(default=None)

    dsdir = repos / 'datasets' / 'test_dataset'
    if not dsdir.joinpath('cldf').exists():
        dsdir.joinpath('cldf').mkdir()
    ds = Dataset(mocker.Mock(
        lexeme_class=Lexeme,
        cognate_class=dataset.Cognate,
        language_class=dataset.Language,
        concept_class=dataset.Concept,
        split_forms=lambda _, s: [s],
        dir=dsdir,
        cldf_dir=dsdir.joinpath('cldf')))
    ds.add_lexemes(
        Value='form',
        Concept='meaning',
        Language_ID='1',
        Parameter_ID='p',
        Segments=['f', 'o'])
    # lid, ipa, concept
    wl = Wordlist(lingpy_util._cldf2wld(ds), row='concept', col='language_id')
    res = list(lingpy_util.wordlist2cognates(wl, 'src'))
    assert isinstance(res[0], dict)


def test_getEvoBibAsBibtex(mocker):
    bib = '<pre>@book{key,\ntitle={The Title}\n}\n</pre>'
    mocker.patch(
        'pylexibank.lingpy_util.get_url', mocker.Mock(return_value=mocker.Mock(text=bib)))
    assert '@book' in lingpy_util.getEvoBibAsBibtex('')


def test_test_sequence():
    if not lingpy_util.LINGPY:
        return  # pragma: no cover
    with pytest.raises(lingpy_util.InvalidString):
        lingpy_util.test_sequence('')

    with pytest.raises(lingpy_util.InvalidString):
        lingpy_util.test_sequence('\n')

    segments, la, clpa, analysis = lingpy_util.test_sequence('a^b')
    assert analysis.general_errors == 1


def test_segmentize():
    if not lingpy_util.LINGPY:
        return  # pragma: no cover
    assert lingpy_util.segmentize('\n') is None
    assert lingpy_util.segmentize('abc') == 'a b c'.split()
