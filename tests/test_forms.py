import pytest

from pylexibank.forms import *


def test_split():
    spec = FormSpec()
    assert spec.split({}, 'x', lexemes={'x': 'x(a);y'}) == ['x', 'y']
    assert spec.split({}, 'x', lexemes={'x': 'x;?'}) == ['x']

    spec.strip_inside_brackets = False
    assert spec.split({}, 'x(a)') == ['x(a)']

    spec = FirstFormOnlySpec()
    assert spec.split({}, 'x', lexemes={'x': 'x;y'}) == ['x']


def test_replacements():
    spec = FormSpec(replacements=[('x', 'y')])
    assert spec.clean('x') == 'y'
    assert spec.clean('y') == 'y'

    with pytest.raises(ValueError):
        FormSpec(replacements=())

    with pytest.raises(ValueError):
        FormSpec(replacements=[(1, 2)])
