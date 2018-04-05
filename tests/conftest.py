# coding: utf8
from __future__ import unicode_literals, print_function, division

import pytest

from clldutils.path import Path, copytree, copy
from clldutils.path import import_module

import pylexibank
from pylexibank.glottolog import Glottolog
from pylexibank.concepticon import Concepticon


@pytest.fixture
def tmppath(tmpdir):
    return Path(str(tmpdir))


@pytest.fixture
def repos(tmppath):
    repos = tmppath / 'lexibank-data'
    copytree(Path(__file__).parent.joinpath('repos'), repos)
    copy(Path(pylexibank.__file__).parent.joinpath('cldf-metadata.json'), repos)
    return repos


@pytest.fixture
def dataset(repos, tmppath):
    mod = import_module(repos / 'datasets' / 'test_dataset')
    return mod.Test(glottolog=Glottolog(tmppath), concepticon=Concepticon(tmppath))
