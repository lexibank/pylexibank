# coding: utf8
from __future__ import unicode_literals, print_function, division

import pytest

from pylexibank.glottolog import Glottolog


@pytest.fixture
def glottolog(repos):
    return Glottolog(repos)


def test_languoid_details(glottolog):
    assert 'abcd1234' in glottolog.languoid_details


def test_macroareas(glottolog):
    assert 'Africa' in [ma.value for ma in glottolog.macroareas_by_glottocode['abcd1234']]


def test_name(glottolog):
    assert 'A Language' in glottolog.glottocode_by_name


def test_iso(glottolog):
    assert 'abc' in glottolog.glottocode_by_iso
