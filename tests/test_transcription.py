import pytest

import pyclts

from pylexibank.transcription import analyze, Analysis


def test_analyze(repos):
    clts = pyclts.CLTS(repos)
    with pytest.raises(ValueError):
        analyze(clts, [], Analysis())

    with pytest.raises(ValueError):
        analyze(clts, ['\n'], Analysis())

    segments, la, clpa, analysis = analyze(clts, ['a', '^', 'b'], Analysis())
    assert segments == ['a', '^', 'b']
    assert analysis.general_errors == 1
