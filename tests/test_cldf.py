# coding: utf8
from __future__ import unicode_literals, print_function, division

from pylexibank.cldf import Dataset


def test_align_cognates(dataset, mocker):
    ds = Dataset(dataset)
    ds.align_cognates()
