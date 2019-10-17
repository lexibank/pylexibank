from pylexibank.forms import *


def test_split():
    spec = FormSpec()
    assert spec.split({}, 'x', lexemes={'x': 'x(a);y'}) == ['x', 'y']
    assert spec.split({}, 'x', lexemes={'x': 'x;?'}) == ['x']

    spec.strip_inside_brackets = False
    assert spec.split({}, 'x(a)') == ['x(a)']

    spec = FirstFormOnlySpec()
    assert spec.split({}, 'x', lexemes={'x': 'x;y'}) == ['x']
