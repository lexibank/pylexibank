import pytest

from pylexibank.transcription import analyze, Analysis


def test_analyze():
    with pytest.raises(ValueError):
        analyze([], Analysis())

    with pytest.raises(ValueError):
        analyze(['\n'], Analysis())

    segments, la, clpa, analysis = analyze(['a', '^', 'b'], Analysis())
    assert segments == ['a', '^', 'b']
    assert analysis.general_errors == 1
