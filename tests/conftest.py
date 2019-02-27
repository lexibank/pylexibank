# coding: utf8
from __future__ import unicode_literals, print_function, division
from tempfile import mkdtemp

import pytest

from clldutils.path import Path, copytree, copy, rmtree, import_module, write_text
from pycldf import Dataset

import pylexibank
from pylexibank.glottolog import Glottolog
from pylexibank.concepticon import Concepticon


@pytest.fixture
def tmppath(tmpdir):
    return Path(str(tmpdir))


@pytest.fixture(scope='session')
def tmpd():
    d = Path(mkdtemp())
    yield d
    rmtree(d)


@pytest.fixture
def cldf_dataset():
    return Dataset.from_metadata(Path(pylexibank.__file__).parent / 'cldf-metadata.json')


@pytest.fixture(scope='session')
def repos(tmpd):
    repos = tmpd / 'lexibank-data'
    copytree(Path(__file__).parent.joinpath('repos'), repos)
    copy(Path(pylexibank.__file__).parent.joinpath('cldf-metadata.json'), repos)
    yield repos


@pytest.fixture(scope='session')
def glottolog(repos):
    return Glottolog(repos)


@pytest.fixture(scope='session')
def concepticon(repos):
    return Concepticon(repos)


@pytest.fixture(scope='session')
def dataset_cldf(repos, tmpd, glottolog, concepticon):
    mod = import_module(repos / 'datasets' / 'test_dataset_cldf')
    return mod.Test(glottolog=glottolog, concepticon=concepticon)


@pytest.fixture(scope='session')
def dataset(repos, tmpd, glottolog, concepticon):
    from mock import Mock

    mod = import_module(repos / 'datasets' / 'test_dataset')
    ds = mod.Test(glottolog=glottolog, concepticon=concepticon)
    ds._install(log=Mock())
    return ds
