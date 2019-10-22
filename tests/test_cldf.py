import pytest

from pylexibank.cldf import LexibankWriter


def test_align_cognates(dataset):
    with LexibankWriter(cldf_spec=dataset.cldf_specs(), dataset=dataset) as ds:
        ds.add_language(ID='a-b')
        with pytest.raises(ValueError):
            ds.add_language(ID='a/b')
        ds.add_languages()
        ds.add_concepts()
        ds.align_cognates()
