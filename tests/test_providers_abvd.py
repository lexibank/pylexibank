import pytest

from clldutils.path import copytree

from pylexibank.providers import abvd


@pytest.fixture
def abvd_dataset(repos, tmp_path, glottolog, concepticon):
    copytree(repos / 'datasets' / 'abvd', tmp_path / 'abvd')

    class Dataset(abvd.BVD):
        id = 'x'
        SECTION = 'y'
        dir = tmp_path / 'abvd'

    return Dataset(glottolog=glottolog, concepticon=concepticon)


def test_Wordlist(abvd_dataset, mocker):
    with abvd_dataset.cldf_writer(mocker.MagicMock()) as ds:
        for wl in abvd_dataset.iter_wordlists():
            wl.to_cldf(ds, {})
            assert wl.name
            assert wl.id


