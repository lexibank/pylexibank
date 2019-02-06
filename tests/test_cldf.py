import pytest

from pylexibank.cldf import Dataset


def test_align_cognates(dataset):
    ds = Dataset(dataset)
    ds.add_language(ID='a-b')
    with pytest.raises(ValueError):
        ds.add_language(ID='a/b')
    ds.add_languages()
    ds.add_concepts()
    ds.align_cognates()
