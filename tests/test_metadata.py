import pytest

from pylexibank.metadata import *


def test_conceptlist():
    md = LexibankMetadata(conceptlist='Swadesh-1964-100', related='abc')
    assert isinstance(md.conceptlist, list)
    assert 'concepticon.clld.org' in md.markdown()


STANDARD_TITLE = """CLDF dataset derived from A et al.'s "Paper" from 1934"""


@pytest.mark.parametrize('title', [
    "",
    STANDARD_TITLE.replace('CLDF', 'cldf'),
    STANDARD_TITLE.replace("et al.'s", 'et al.’s'),
    STANDARD_TITLE.replace('"', "'"),
    STANDARD_TITLE.replace('1934', '34'),
])
def test_invalid_standard_title(title):
    with pytest.raises(AssertionError):
        check_standard_title(title)


def test_valid_standard_title():
    assert check_standard_title(STANDARD_TITLE) is None
    assert check_standard_title(STANDARD_TITLE.replace(" et al.'s", "brams'")) is None


def test_get_creators_and_contributors():
    assert len(get_creators_and_contributors([])[0]) == 0
    cr, co = get_creators_and_contributors(['a|role', '---|---', 'c|staff'], strict=False)
    assert len(cr) == 0 and len(co) == 1

    with pytest.raises(KeyError):
        get_creators_and_contributors(['a|role', '---|---', 'c|staff'], strict=True)

    assert len(get_creators_and_contributors(['a|role', '---|---', 'c|author'])[0]) == 1
    assert len(get_creators_and_contributors(['a|role', '---|---', 'c|author', 'a', 'e|f'])[0]) == 1

    with pytest.raises(AssertionError):
        get_creators_and_contributors(['---|---', 'c|d'])
