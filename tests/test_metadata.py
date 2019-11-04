from pylexibank.metadata import *


def test_conceptlist():
    md = LexibankMetadata(conceptlist='Swadesh-1964-100')
    assert isinstance(md.conceptlist, list)
    assert 'concepticon.clld.org' in md.markdown()
