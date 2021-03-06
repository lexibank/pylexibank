import pytest

from pylexibank.forms import *


def test_split():
    spec = FormSpec()
    assert spec.split({}, 'x', lexemes={'x': 'x(a);y'}) == ['x', 'y']
    assert spec.split({}, 'x', lexemes={'x': 'x;?'}) == ['x']

    spec.strip_inside_brackets = False
    assert spec.split({}, 'x(a)') == ['x(a)']

    spec = FormSpec(separators='|')
    assert spec.split(None, 'x|y') == ['x', 'y']
    assert spec.split(None, 'x;y') == ['x;y']

    spec = FormSpec(first_form_only=True)
    assert spec.split({}, 'x', lexemes={'x': 'x;y'}) == ['x']


def test_markdown():
    spec = FormSpec()
    assert spec.as_markdown()


def test_normalize_whitespace():
    spec = FormSpec()
    assert spec.clean(' a\t b\n') == 'a b'

    spec = FormSpec(normalize_whitespace=False, strip_inside_brackets=False)
    assert spec.clean(' a\t b\n') == ' a\t b\n'


def test_normalize_unicode():
    spec = FormSpec(normalize_unicode='NFD', separators='\u0308')
    # The combining diaresis is used as separator:
    assert len(spec.split(None, 'äb')) == 2


def test_separators():
    with pytest.raises(ValueError):
        FormSpec(separators=5)

    with pytest.raises(ValueError):
        FormSpec(separators=['ab'])


def test_replacements():
    spec = FormSpec(replacements=[('x', 'y')])
    assert spec.clean('x') == 'y'
    assert spec.clean('y') == 'y'

    with pytest.raises(ValueError):
        FormSpec(replacements=())

    with pytest.raises(ValueError):
        FormSpec(replacements=[(1, 2)])
