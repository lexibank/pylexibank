from argparse import Namespace

import pytest

from pylexibank.cldf import LexibankWriter


def test_align_cognates(dataset, clts, mocker):
    with LexibankWriter(
        cldf_spec=dataset.cldf_specs(),
        dataset=dataset,
        args=Namespace(clts=mocker.Mock(api=clts))
    ) as ds:
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

        with pytest.raises(ValueError):
            ds.add_form_with_segments()

        with pytest.raises(ValueError):
            ds.add_forms_from_value(Language_ID='l', Parameter_ID='p', Value='x', Segments=['x'])

        with pytest.raises(ValueError):
            ds.add_forms_from_value(Language_ID='l', Parameter_ID='p', Value='x', Form='x')

        with pytest.raises(ValueError):
            ds.add_form()

        with pytest.raises(ValueError):
            ds.add_form(
                Language_ID='l', Parameter_ID='p', Value='x', Form='x', Segments=['x'])

        ds.cldf['FormTable', 'Segments'].separator = '+'
        lex = ds.add_form_with_segments(
            Language_ID='l', Parameter_ID='p', Value='x', Form='x', Segments=['x'])
        assert lex['Segments'] == ['u']
