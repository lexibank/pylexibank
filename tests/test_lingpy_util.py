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
        tr_analyses={},
        cldf_dir=dsdir.joinpath('cldf')))
    ds2 = Dataset(mocker.Mock(
        lexeme_class=Lexeme,
        cognate_class=dataset.Cognate,
        language_class=dataset.Language,
        concept_class=dataset.Concept,
        split_forms=lambda _, s: [s],
        dir=dsdir,
        tr_analyses={},
        cldf_dir=dsdir.joinpath('cldf')))
    ds2.add_form_with_segments(
        Value='form,form2',
        Concept='meaning',
        Language_ID='1',
        Parameter_ID='p',
        Form='form',
        Segments=['f', 'o']
        )
    ds.add_forms_from_value(
            Value='form,form2',
            Concept='meaning',
            Language_ID='1',
            Parameter_ID='p'
            )
    # lid, ipa, concept
    wl = Wordlist(lingpy_util._cldf2wld(ds2), row='concept', col='language_id')
    res = list(lingpy_util.wordlist2cognates(wl, 'src'))
    assert isinstance(res[0], dict)
