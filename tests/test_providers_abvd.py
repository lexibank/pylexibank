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
    with abvd_dataset.cldf_writer(mocker.MagicMock()) as ds:
        for wl in abvd_dataset.iter_wordlists():
            wl.to_cldf(ds, {})
            assert wl.name
            assert wl.id


