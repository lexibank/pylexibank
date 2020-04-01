from pylexibank.profile import Profile


def test_init():
    prf = Profile({'Grapheme': 'x', 'IPA': 'y'})
    assert prf.graphemes['^']['IPA'] is None


def test_sort():
    prf = Profile({'Grapheme': 'ab', 'IPA': 'z'}, {'Grapheme': 'x', 'IPA': 'y'})
    assert list(prf.graphemes.keys())[0] == 'ab'
    prf.sort()
    assert list(prf.graphemes.keys())[0] == '^'
    assert list(prf.graphemes.keys())[-1] == 'ab'


def test_trim():
    prf = Profile(
        {'Grapheme': 'ab', 'IPA': 'x y'},
        {'Grapheme': 'a', 'IPA': 'x'},
        {'Grapheme': 'b', 'IPA': 'y'},
    )
    assert prf.trim() == 1
    assert 'ab' not in prf.graphemes


def test_augment():
    prf = Profile(
        {'Grapheme': '^a', 'IPA': 'z'},
        {'Grapheme': 'a', 'IPA': 'x'},
        {'Grapheme': 'b', 'IPA': 'y'},
    )
    prf.augment(['aab', 'ba', 'aba'])
    assert prf.graphemes['^a']['FREQUENCY'] == 2
    assert prf.graphemes['a']['FREQUENCY'] == 3
