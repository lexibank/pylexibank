import pytest

from pylexibank.cldf import LexibankWriter


def test_align_cognates(dataset):
    with LexibankWriter(cldf_spec=dataset.cldf_specs(), dataset=dataset) as ds:
        ds.add_language(ID='a-b')
        with pytest.raises(ValueError):
            ds.add_language(ID='a/b')
        lmap = ds.add_languages(lookup_factory='Name')
        assert isinstance(lmap, dict)
        assert lmap['abcd'] == '1'
        cids = ds.add_concepts()
        assert isinstance(cids, list)
        assert '1' in cids
        ds.align_cognates()
