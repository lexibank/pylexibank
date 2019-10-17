import pytest
from pathlib import Path

from clldutils.path import copytree
from pycldf.sources import Source

from pylexibank.providers import abvd


@pytest.fixture
def abvd_dataset(repos, tmpdir, glottolog, concepticon):
    copytree(repos / 'datasets' / 'abvd', str(tmpdir.join('abvd')))

    class Dataset(abvd.BVD):
        id = 'x'
        SECTION = 'y'
        dir = Path(str(tmpdir.join('abvd')))

    return Dataset(glottolog=glottolog, concepticon=concepticon)


def test_Wordlist(abvd_dataset, mocker):
    with abvd_dataset.cldf_writer(mocker.Mock()) as ds:
        for wl in abvd_dataset.iter_wordlists({'1': 'bali1278'}, None):
            wl.to_cldf(ds, {}, citekey='x',source='s')
            assert wl.name
            assert wl.id
            assert wl.md()


def test_Wordlist_2(abvd_dataset, mocker):
    with abvd_dataset.cldf_writer(mocker.Mock()) as ds:
        for wl in abvd_dataset.iter_wordlists({'1': 'bali1278'}, None):
            wl.to_cldf(ds, {}, citekey='x', source=[Source('a', 'b', **dict(title='t'))])


def test_Wordlist_3(abvd_dataset, mocker):
    with abvd_dataset.cldf_writer(mocker.Mock()) as ds:
        for wl in abvd_dataset.iter_wordlists({'1': 'bali1278'}, None):
            wl.to_cldf(ds, {})
