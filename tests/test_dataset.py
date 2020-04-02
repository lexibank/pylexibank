import sys
import json
import importlib
import pathlib

import pytest
from clldutils.path import sys_path
from cldfbench.dataset import NOOP

from pylexibank import Lexeme, Dataset
from pylexibank.dataset import Unmapped


def import_module(p):
    with sys_path(p.parent):
        if p.stem in sys.modules:
            return importlib.reload(sys.modules[p.stem])
        return importlib.import_module(p.stem)


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


def test_Dataset_tokenizer(tmpdir):
    etc = pathlib.Path(str(tmpdir)).joinpath('etc')
    etc.mkdir()
    orth_dir = etc.joinpath('orthography')
    orth_dir.mkdir()
    orth_dir.joinpath('l1.tsv').write_text('Grapheme\tIPA\na\tb')

    class DS(Dataset):
        id = '1'
        dir = etc.parent

    ds = DS()
    assert ds.tokenizer({}, 'a', profile='l1') == ['b']
    assert ds.tokenizer({'Language_ID': 'l1'}, 'a') == ['b']

    etc.joinpath('orthography.tsv').write_text('Grapheme\tIPA\na\tc')
    ds = DS()
    assert ds.tokenizer({}, 'a') == ['c']


def test_BaseDataset(mocker, repos):
    class TestDataset(Dataset):
        dir = repos / 'datasets' / 'test_dataset'
        id = 'abc'

    ds = TestDataset(glottolog=mocker.Mock(), concepticon=mocker.Mock())
    assert ds.cmd_download(mocker.Mock()) == NOOP
    assert ds.cmd_makecldf(mocker.Mock()) == NOOP
    assert ds.sources
    assert ds.concepts
    assert ds.languages
    assert len(ds.raw_dir.read_bib('sources_ext.bib')) == 96

    assert not ds.stats
    ds.dir.write('README.json', json.dumps({'a': 1}))
    assert ds.stats['a'] == 1


@pytest.mark.parametrize(
    'string,segments,graphemes',
    [
        ('^b$', 'b', '^ ^ b $ $'),  # context marker is stripped
        ('aba', 'c b z', '^a b a$'),  # "a" is treated differently depending on context
        ('bab', 'b a b', '^ b a b $'),  # "a" is treated differently depending on context
    ]
)
def test_tokenizer(repos, string, segments, graphemes):
    import warnings

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        mod = import_module(repos / 'datasets' / 'test_dataset_cldf' / 'tdc')
        dataset = mod.Test()
        item = {}
        assert dataset.tokenizer(item, string) == segments.split()
        assert item['Graphemes'] == graphemes
