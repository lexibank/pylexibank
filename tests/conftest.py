import os
import sys
from pathlib import Path
from argparse import Namespace
import importlib
import shutil

import pytest

from clldutils.path import copytree, copy, sys_path
from pycldf import Dataset
from cldfbench.catalogs import CachingConcepticonAPI, CachingGlottologAPI, CLTSAPI
from cldfcatalog.repository import get_test_repo

import pylexibank


@pytest.fixture
def git_repo(tmpdir):
    return get_test_repo(str(tmpdir), remote_url='https://github.com/lexibank/dataset.git')


@pytest.fixture
def cldf_dataset():
    return Dataset.from_metadata(Path(pylexibank.__file__).parent / 'cldf-metadata.json')


@pytest.fixture
def git_repo_factory(git_repo):
    def factory(d):
        target = d / '.git'
        if not target.exists():
            shutil.copytree(os.path.join(git_repo.working_dir, '.git'), str(target))
    return factory


@pytest.fixture
def repos(tmp_path, git_repo_factory):
    repos = tmp_path / 'lexibank-data'
    copytree(Path(__file__).parent.joinpath('repos'), repos)
    git_repo_factory(repos)
    git_repo_factory(repos / 'datasets' / 'test_dataset')
    git_repo_factory(repos / 'datasets' / 'test_dataset_cldf')
    copy(Path(pylexibank.__file__).parent.joinpath('cldf-metadata.json'), repos)
    yield repos


@pytest.fixture
def glottolog(repos):
    return CachingGlottologAPI(repos)


@pytest.fixture
def concepticon(repos):
    return CachingConcepticonAPI(repos)


@pytest.fixture
def clts(repos):
    return CLTSAPI(repos)


def _get_dataset(repos, module, glottolog, concepticon):
    d, _, module = module.partition('.')
    with sys_path(repos / 'datasets' / d):
        if module in sys.modules:
            mod = importlib.reload(sys.modules[module])
        else:
            mod = importlib.import_module(module)
    return mod.Test(glottolog=glottolog, concepticon=concepticon)


@pytest.fixture
def dataset_factory(repos, glottolog, concepticon):
    def factory(module):
        return _get_dataset(repos, module, glottolog, concepticon)
    return factory


@pytest.fixture
def dataset_cldf(repos, glottolog, concepticon):
    return _get_dataset(repos, 'test_dataset_cldf.tdc', glottolog, concepticon)


@pytest.fixture
def dataset_cldf_capitalisation(repos, glottolog, concepticon):
    return _get_dataset(repos, 'test_dataset_cldf_capitalisation.tdc', glottolog, concepticon)


@pytest.fixture
def dataset(repos, glottolog, concepticon, clts, mocker):
    ds = _get_dataset(repos, 'test_dataset.td', glottolog, concepticon)
    ds._cmd_makecldf(
        Namespace(log=mocker.Mock(), clts=mocker.Mock(api=clts), verbose=True, dev=False))
    return ds


@pytest.fixture
def dataset_no_cognates(repos, glottolog, concepticon, clts):
    return _get_dataset(repos, 'test_dataset_no_cognates.tdn', glottolog, concepticon)


@pytest.fixture
def sndcmp(repos, glottolog, concepticon, clts):
    return _get_dataset(repos, 'sndcmp.ts', glottolog, concepticon)
