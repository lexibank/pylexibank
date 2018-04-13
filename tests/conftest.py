# coding: utf8
from __future__ import unicode_literals, print_function, division
from tempfile import mkdtemp

import pytest

from clldutils.path import Path, copytree, copy, rmtree
from clldutils.path import import_module

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


@pytest.fixture(scope='session')
def repos(tmpd):
    repos = tmpd / 'lexibank-data'
    copytree(Path(__file__).parent.joinpath('repos'), repos)
    copy(Path(pylexibank.__file__).parent.joinpath('cldf-metadata.json'), repos)
    yield repos


@pytest.fixture(scope='session')
def dataset(repos, tmpd):
    mod = import_module(repos / 'datasets' / 'test_dataset')
    return mod.Test(glottolog=Glottolog(tmpd), concepticon=Concepticon(tmpd))
