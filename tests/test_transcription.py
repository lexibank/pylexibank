import pytest

import pyclts

from pylexibank.transcription import analyze, Analysis, Report, analyze_segments


def test_analyze(repos):
    clts = pyclts.CLTS(repos)
    with pytest.raises(ValueError):
        analyze(clts, [], Analysis())

    with pytest.raises(ValueError):
        analyze(clts, ['\n'], Analysis())

    segments, la, clpa, analysis = analyze(clts, ['a', '^', 'b'], Analysis())
    assert segments == ['a', '^', 'b']
    assert analysis.general_errors == 1


def test_analyze_segments(clts):
    rep = Report()
    analyze_segments(
        clts,
        {'ID': '1', 'Language_ID': 'l', 'Parameter_ID': 'p', 'Form': 'abc',
                   'Segments': ['a', 'b c', 'd']},
        rep,
        True)
    assert len(rep.by_language['l'].segments) == 4


def test_Report(clts):
    invalid_bipa = "a\u033c\u02d0"
    rep = Report()
    for form in [
        {'ID': '1', 'Language_ID': 'l', 'Parameter_ID': 'p', 'Form': 'abc',
         'Segments': ['a', 'b', 'c']},
        {'ID': '1', 'Language_ID': 'l', 'Parameter_ID': 'p', 'Form': 'abc',
         'Segments': ['+', 'b', invalid_bipa, 'c']},
        {'ID': '1', 'Language_ID': 'l', 'Parameter_ID': 'p', 'Form': '',
         'Segments': []},
    ]:
        analyze_segments(clts, form, rep, False)
    rep.compute_stats()
    assert 'l' in rep.by_language
    assert len(rep.stats.segments) == 5
    assert rep.stats.bad_words_count == 1
    assert f'<s> {invalid_bipa}' in rep.stats.bad_words[0][-1]
    assert rep.stats.invalid_words_count == 1
    assert '✓' in str(rep)
    assert 'stats' in rep.to_json()
