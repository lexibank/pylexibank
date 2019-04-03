# coding: utf8
from __future__ import unicode_literals, print_function, division

import pytest


@pytest.fixture
def config(dataset):
    class Config(dict):
        datasets = [dataset]

    return Config()


def test_with_dataset(mocker, capsys, config):
    from pylexibank.commands.util import with_dataset

    def func(*args, **kw):
        print('hello!')

    log = mocker.Mock()
    with_dataset(mocker.Mock(cfg=config, args=['test_dataset'], log=log), func)
    out, err = capsys.readouterr()
    assert 'hello!' in out
    assert log.info.called


def test_db(dataset, mocker):
    from pylexibank.commands.util import _load, _unload
    from pylexibank.commands.misc import db

    db_ = dataset.dir / 'db.sqlite'
    _load(dataset, db=db_)
    _unload(dataset, db=db_)
    db(mocker.Mock(db=db_))


def test_orthography(config, mocker):
    from pylexibank.commands.misc import orthography

    orthography(mocker.Mock(cfg=config, args=['test_dataset']))


def test_workflow(repos, mocker, capsys, dataset, tmppath, config):
    from pylexibank.commands.misc import ls, bib, clean, diff, makecldf, download, requirements

    config.update({'paths': {'lexibank': repos.as_posix()}})

    def _args(*args):
        return mocker.Mock(
            cfg=config,
            log=mocker.Mock(),
            db=tmppath / 'db.sqlite',
            verbose=True,
            args=list(args))

    download(_args('test_dataset'))
    out, err = capsys.readouterr()

    clean(_args('test_dataset'))
    diff(_args('test_dataset'))

    makecldf(_args('test_dataset'))
    out, err = capsys.readouterr()

    ls(_args('test_dataset', 'license'))
    out, err = capsys.readouterr()

    assert not dataset.stats

    bib(_args())
    assert repos.joinpath('lexibank.bib').exists()
    out, err = capsys.readouterr()

    dataset.cldf_dir.joinpath('tmp').mkdir()
    dataset._clean()
    assert not dataset.cldf_dir.joinpath('tmp').exists()

    requirements(_args())
    out, err = capsys.readouterr()
    assert 'git+https' in out
