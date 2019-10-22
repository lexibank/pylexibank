import pytest

from pylexibank import Dataset
from pylexibank.report import build_status_badge, report


@pytest.fixture
def ds(tmppath, git_repo_factory):
    git_repo_factory(tmppath)
    ds_ = Dataset()
    ds_.dir = tmppath
    ds_.dir.joinpath('.travis.yml').write_text('#', encoding='utf8')
    ds_.dir.joinpath('NOTES.md').write_text('#', encoding='utf8')
    return ds_


def test_no_travis_badge():
    assert not build_status_badge(Dataset())


def test_travis_badge(ds):
    assert build_status_badge(ds)


def test_report(ds):
    assert report(ds)


def test_report_full(dataset):
    assert report(dataset)
