import pathlib
import shlex

import pytest

from cldfbench.__main__ import main


def _main(cmd, **kw):
    main(['--no-config'] + shlex.split(cmd), **kw)


def test_makecldf(repos, dataset):
    _main('lexibank.makecldf {0} --glottolog {1} --concepticon {1} --clts {1}'.format(
        str(dataset.dir / 'td.py'),
        str(repos),
    ))


def test_ls(repos, tmpdir, dataset):
    _main('lexibank.load --db {3} {0} --glottolog {1} --concepticon {2}'.format(
        str(dataset.dir / 'td.py'),
        str(repos),
        str(repos),
        str(tmpdir.join('db')),
    ))
    _main('lexibank.ls {0} --all --db {1}'.format(
        str(dataset.dir / 'td.py'),
        str(tmpdir.join('db'))))
    _main('lexibank.unload --db {1} {0}'.format(
        str(dataset.dir / 'td.py'),
        str(tmpdir.join('db')),
    ))


def test_db(tmpdir, mocker):
    mocker.patch('pylexibank.commands.db.subprocess', mocker.Mock(return_value=0))
    _main('lexibank.db --db {0}'.format(str(tmpdir.join('db'))))


def test_check_phonotactics(dataset):
    _main('lexibank.check_phonotactics {0}'.format(str(dataset.dir / 'td.py')))


def test_check_profile(dataset, repos):
    _main('lexibank.check_profile {0} --clts {1}'.format(str(dataset.dir / 'td.py'), repos))


def test_init_profile(dataset, repos):
    _main('lexibank.init_profile {0} --clts {1} -f --context'.format(
        str(dataset.dir / 'td.py'), repos))
    with pytest.raises(SystemExit):
        _main('lexibank.init_profile {0} --clts {1}'.format(str(dataset.dir / 'td.py'), repos))


def test_readme(dataset, repos):
    _main('lexibank.readme {0} --glottolog {1}'.format(str(dataset.dir / 'td.py'), repos))


def test_new(tmpdir, mocker):
    mocker.patch('cldfbench.metadata.input', mocker.Mock(return_value='abc'))
    _main('new --template lexibank_simple --out ' + str(tmpdir))
    assert pathlib.Path(str(tmpdir)).joinpath('abc', 'CONTRIBUTORS.md').exists()
