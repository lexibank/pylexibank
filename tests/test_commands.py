import shlex
import logging
import pathlib
import argparse

import pytest

from cldfbench.__main__ import main
from pylexibank import cli_util


def test_warning(caplog):
    cli_util.warning(
        argparse.Namespace(log=logging.getLogger(__name__)),
        'message in a bottle',
        dataset=argparse.Namespace(id='abc')
    )
    assert caplog.records[-1].levelname == 'WARNING'


def _main(cmd, **kw):
    main(['--no-config'] + shlex.split(cmd), **kw)


def test_makecldf(repos, dataset, dataset_cldf, dataset_no_cognates, sndcmp, tmpdir):
    _main('lexibank.makecldf {0} --glottolog {1} --concepticon {1} --clts {1}'.format(
        str(dataset.dir / 'td.py'),
        str(repos),
    ))
    assert 'Papunesia' in dataset.cldf_dir.joinpath('languages.csv').read_text(encoding='utf8')

    _main('lexibank.makecldf {0} --dev --glottolog {1} --concepticon {1} --clts {1}'.format(
        str(dataset.dir / 'td.py'),
        str(repos),
    ))
    assert 'Papunesia' not in dataset.cldf_dir.joinpath('languages.csv').read_text(encoding='utf8')
    assert '### Replacement' in dataset.dir.joinpath('FORMS.md').read_text(encoding='utf8')

    _main('lexibank.makecldf {0} --glottolog {1} --concepticon {1} --clts {1}'.format(
        str(sndcmp.dir / 'ts.py'),
        str(repos),
    ))
    assert 'Bislama_Gloss' in sndcmp.cldf_dir.joinpath('parameters.csv').read_text(encoding='utf8')
    assert 'e56a5fc78ae5a66e783c17bc30019568' in sndcmp.cldf_dir.joinpath('media.csv').read_text(encoding='utf8')

    with pytest.raises(ValueError):
        _main('lexibank.makecldf {0} --glottolog {1} --concepticon {1} --clts {1}'.format(
            str(dataset_cldf.dir / 'tdc.py'),
            str(repos),
        ))

    _main('lexibank.makecldf {0} --glottolog {1} --concepticon {1} --clts {1}'.format(
        str(dataset_no_cognates.dir / 'tdn.py'),
        str(repos),
    ))
    assert not dataset_no_cognates.cldf_dir.joinpath('cognates.csv').exists()
    _main('lexibank.load --db {3} {0} --glottolog {1} --concepticon {2}'.format(
        str(dataset_no_cognates.dir / 'tdn.py'),
        str(repos),
        str(repos),
        str(tmpdir.join('db')),
    ))


def test_check(dataset_cldf):
    _main('lexibank.check {0}'.format(str(dataset_cldf.dir / 'tdc.py')))


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
    assert dataset.dir.joinpath('FORMS.md').exists()
    assert '# Contributors' in dataset.dir.joinpath('README.md').read_text(encoding='utf8')


def test_new(tmpdir, mocker):
    mocker.patch('cldfbench.metadata.input', mocker.Mock(return_value='abc'))
    _main('new --template lexibank_simple --out ' + str(tmpdir))
    assert pathlib.Path(str(tmpdir)).joinpath('abc', 'CONTRIBUTORS.md').exists()

    mocker.patch('cldfbench.metadata.input', mocker.Mock(return_value='cde'))
    _main('new --template lexibank_combined --out ' + str(tmpdir))
    assert '{{' not in pathlib.Path(str(tmpdir)).joinpath(
        'cde', 'lexibank_cde.py').read_text(encoding='utf8')

