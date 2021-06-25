from argparse import Namespace

import pytest
import attr

from pylexibank.cldf import LexibankWriter
from pylexibank import Language, Dataset
from clldutils.jsonlib import load


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

        with pytest.raises(ValueError):
            ds.add_concept(ID='1', Concepticon_ID='1', Concepticon_Gloss='xyz')

        ds.cldf['FormTable', 'Segments'].separator = '+'
        lex = ds.add_form_with_segments(
            Language_ID='l', Parameter_ID='p', Value='x', Form='x', Segments=['x', 'y'])
        assert lex['Segments'] == ['a', 'b']


def test_reqs(tmp_path, mocker, clts):
    class D(Dataset):
        dir = tmp_path
        id = 'x'

        def cmd_makecldf(self, args):
            args.writer.add_language(ID='l')
            args.writer.add_concept(ID='c')
            args.writer.add_form_with_segments(
                Language_ID='l', Parameter_ID='c', Value='x', Form='x', Segments=['x', 'y'])

    D()._cmd_makecldf(Namespace(
        log=mocker.Mock(), dev=False, verbose=False, clts=mocker.Mock(api=clts)))
    md =  load(tmp_path.joinpath('cldf', 'cldf-metadata.json'))
    reqs = {o['dc:title']: o for o in md['prov:wasGeneratedBy']}
    assert tmp_path.joinpath('cldf', reqs['lingpy-rcParams']['dc:relation']).exists()
    assert reqs['python-packages'] and reqs['python']


def test_custom_columns(tmp_path, clts, mocker):
    @attr.s
    class Variety(Language):
        """
        abcdefg
        """
        x = attr.ib(
            default=None,
            metadata={'separator': ';', 'dc:description': "-+-+-"},
        )
    class D(Dataset):
        dir = tmp_path
        id = 'x'
        language_class = Variety

        def cmd_makecldf(self, args):
            args.writer.add_language(ID='l', x=['x', 'y'])
            args.writer.add_concept(ID='c')
            args.writer.add_form_with_segments(
                Language_ID='l', Parameter_ID='c', Value='x', Form='x', Segments=['x', 'y'])

    D()._cmd_makecldf(Namespace(
        log=mocker.Mock(), dev=False, verbose=False, clts=mocker.Mock(api=clts)))
    assert 'x;y' in tmp_path.joinpath('cldf', 'languages.csv').read_text(encoding='utf8')
    md = tmp_path.joinpath('cldf', 'cldf-metadata.json').read_text(encoding='utf8')
    assert '-+-+-' in md
    assert 'abcdefg' in md
