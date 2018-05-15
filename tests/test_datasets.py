# coding: utf8
from __future__ import unicode_literals, print_function, division
import logging

import pytest
from clldutils.loglib import Logging

from pylexibank.dataset import Lexeme, Unmapped, Dataset, NOOP


def test_Item():
    with pytest.raises(TypeError):
        Lexeme()

    with pytest.raises(ValueError):
        Lexeme(ID=1, Form='a', Value='', Language_ID='l', Parameter_ID='p')


def test_Unmapped(capsys):
    unmapped = Unmapped()
    unmapped.add_language(ID='tl', Name='the language')
    unmapped.add_concept(ID='tc', Name='the concept')
    unmapped.pprint()
    out, err = capsys.readouterr()
    assert 'tc,"the concept",,' in out.split('\n')


def test_BaseDataset(mocker, repos):
    class TestDataset(Dataset):
        dir = repos / 'datasets' / 'test_dataset'

    ds = TestDataset(glottolog=mocker.Mock(), concepticon=mocker.Mock())
    assert ds.cmd_download() == NOOP
    assert ds.cmd_install() == NOOP
    assert ds.tokenizer(None, 'a') == ['b']
    assert ds.sources


def test_Dataset(dataset, capsys):
    dataset.cmd_download()
    dataset.cmd_install()
    assert dataset.tokenizer
