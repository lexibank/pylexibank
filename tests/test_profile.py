import logging
import pathlib

from pylexibank.profile import Profile


def test_init():
    prf = Profile({'Grapheme': 'x', 'IPA': 'y'})
    assert prf.graphemes['^']['IPA'] is None


def test_sort(clts):
    prf = Profile({'Grapheme': 'ab', 'IPA': 'z'}, {'Grapheme': 'x', 'IPA': 'y'})
    assert list(prf.graphemes.keys())[0] == 'ab'
    prf.sort()
    assert list(prf.graphemes.keys())[0] == '^'
    assert list(prf.graphemes.keys())[-1] == 'ab'

    prf.sort(clts=clts)
    assert list(prf.graphemes.keys())[-1] == 'x'


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


def test_write(tmpdir):
    fname = pathlib.Path(str(tmpdir)) / 'profile.tsv'
    prf = Profile({'Grapheme': 'ab', 'IPA': 'z'}, {'Grapheme': 'x', 'IPA': 'y'})
    prf.write(fname)
    assert Profile.from_file(fname).graphemes == prf.graphemes


def test_clean(clts):
    prf = Profile(
        {'Grapheme': 'a', 'IPA': 'ƛ', 'CODEPOINTS': ''},
        {'Grapheme': 'b', 'IPA': 'b/ƛ', 'CODEPOINTS': ''},
    )
    prf.clean(clts)
    assert prf.graphemes['a']['IPA'] != 'ƛ'
    assert prf.graphemes['a']['CODEPOINTS'] == 'U+0061'
    assert prf.graphemes['b']['IPA'] == 'b/tɬ'


def test_check(caplog, tmpdir, clts):
    prf_path = pathlib.Path(str(tmpdir)) / 'profile.tsv'

    prf_path.write_text('Grapheme\tIPA\na\tx\na\tx\n')
    prf = Profile.from_file(prf_path)
    prf.check(log=logging.getLogger(__name__))
    assert caplog.records[-1].levelname == 'WARNING'

    prf_path.write_text('Grapheme\tIPA\na\tx\na\ty\n')
    prf.check(log=logging.getLogger(__name__))
    assert caplog.records[-1].levelname == 'ERROR'

    prf_path.write_text('Grapheme\tIPA\na\t°\n')
    prf.check(clts=clts, log=logging.getLogger(__name__))
    assert caplog.records[-1].levelname == 'ERROR'
