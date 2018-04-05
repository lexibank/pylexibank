# coding: utf8
from __future__ import unicode_literals, print_function, division
import logging

import pytest
from clldutils.loglib import Logging

from pylexibank import dataset


def test_Item():
    with pytest.raises(TypeError):
        dataset.Lexeme()

    with pytest.raises(ValueError):
        dataset.Lexeme(ID=1, Form='a', Value='', Language_ID='l', Parameter_ID='p')


def test_Unmapped(capsys):
    unmapped = dataset.Unmapped()
    unmapped.add_language(id='tl', name='the language')
    unmapped.add_concept(id='tc', gloss='the concept')
    unmapped.pprint()
    out, err = capsys.readouterr()
    assert 'tc,"the concept",,' in out.split('\n')


def test_Dataset():
    ds = dataset.Dataset()
    with ds.debug():
        pass
    with Logging(ds.log, logging.CRITICAL):
        ds.cmd_download()
        ds.cmd_install()
    assert ds.get_tokenizer() is None
