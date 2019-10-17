import os
import sys
from pathlib import Path
from argparse import Namespace
import importlib
import shutil

import pytest

from clldutils.path import copytree, copy, sys_path
from pycldf import Dataset
from cldfbench.catalogs import CachingConcepticonAPI, CachingGlottologAPI
from cldfcatalog.repository import get_test_repo

import pylexibank


@pytest.fixture
def tmppath(tmpdir):
    return Path(str(tmpdir))


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
def repos(tmppath, git_repo_factory):
    repos = tmppath / 'lexibank-data'
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
def dataset_cldf(repos, glottolog, concepticon):
    with sys_path(repos / 'datasets' / 'test_dataset_cldf'):
        if 'tdc' in sys.modules:
            mod = importlib.reload(sys.modules['tdc'])
        else:
            mod = importlib.import_module('tdc')
    return mod.Test(glottolog=glottolog, concepticon=concepticon)


@pytest.fixture
def dataset(repos, glottolog, concepticon):
    from mock import Mock

    with sys_path(repos / 'datasets' / 'test_dataset'):
        if 'td' in sys.modules:
            mod = importlib.reload(sys.modules['td'])
        else:
            mod = importlib.import_module('td')
    ds = mod.Test(glottolog=glottolog, concepticon=concepticon)
    ds._cmd_makecldf(Namespace(log=Mock(), verbose=True))
    return ds
