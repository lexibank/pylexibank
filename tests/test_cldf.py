# coding: utf8
from __future__ import unicode_literals, print_function, division

import pytest

from pylexibank.cldf import Dataset


def test_align_cognates(dataset, mocker):
    ds = Dataset(dataset)
    ds.add_language(ID='a-b')
    with pytest.raises(ValueError):
        ds.add_language(ID='a/b')
    ds.align_cognates()
