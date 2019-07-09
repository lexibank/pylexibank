import json

import pytest
from clldutils.path import import_module

from pylexibank.dataset import Lexeme, Unmapped, Dataset, NOOP, Metadata


def test_Metadata():
    md = Metadata(license='CC-BY-1.0')
    assert md.known_license
    assert md.common_props

    md = Metadata()
    assert md.common_props

    md = Metadata(license='CC-BY')
    assert md.common_props['dc:license'] == 'CC-BY'


def test_Item():
    with pytest.raises(TypeError):
        Lexeme()

    with pytest.raises(ValueError):
        Lexeme(ID=1, Form='a', Value='', Language_ID='l', Parameter_ID='p')


def test_Unmapped(capsys):
    unmapped = Unmapped()
    unmapped.add_language(ID='tl', Name='the language')
    unmapped.add_concept(ID='tc', Name='the concept')
    unmapped.pprint()
    out, err = capsys.readouterr()
    assert 'tc,"the concept",,' in out.split('\n')


def test_invalid_dataset():
    class Test(Dataset):
        pass

    with pytest.raises(ValueError):
        Test()


def test_BaseDataset(mocker, repos):
    class TestDataset(Dataset):
        dir = repos / 'datasets' / 'test_dataset'
        id = 'abc'

    ds = TestDataset(glottolog=mocker.Mock(), concepticon=mocker.Mock())
    assert ds.cmd_download() == NOOP
    assert ds.cmd_install() == NOOP
    assert ds.sources
    assert ds.concepts
    assert ds.languages
    assert len(ds.raw.read_bib('sources_ext.bib')) == 96

    assert not ds.stats
    ds.dir.write('README.json', json.dumps({'a': 1}))
    assert ds.stats['a'] == 1


@pytest.mark.parametrize(
    'string,tokens',
    [
        ('^b$', 'b'),  # context marker is stripped
        ('aba', 'c b z'),  # "a" is treated differently depending on context
        ('bab', 'b a b'),  # "a" is treated differently depending on context
    ]
)
def test_tokenizer(repos, string, tokens):
    import warnings

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        mod = import_module(repos / 'datasets' / 'test_dataset_cldf')
        dataset = mod.Test()
        assert dataset.tokenizer(None, string) == tokens.split()


def test_Dataset(dataset, capsys):
    dataset.cmd_download()
    dataset.cmd_install()
    assert dataset.tokenizer
