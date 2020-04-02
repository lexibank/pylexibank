import shlex
import logging
import pathlib
import argparse

import pytest

from csvw import dsv
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


def test_makecldf_concepticon_concepts(repos, tmpdir):
    d = repos / 'datasets' / 'test_dataset_concepticon_concepts'
    _main('lexibank.makecldf {0} --glottolog {1} --concepticon {1} --clts {1}'.format(
        str(d / 'tdcc.py'),
        str(repos),
    ))
    assert d.joinpath('cldf', 'parameters.csv').read_text(encoding='utf8').splitlines()[0] == \
        'ID,Name,Concepticon_ID,Concepticon_Gloss,NUMBER,ENGLISH,CHINESE,PAGE'


def test_makecldf_multi_profiles(repos):
    d = repos / 'datasets' / 'test_dataset_multi_profile'
    _main('lexibank.makecldf {0} --glottolog {1} --concepticon {1} --clts {1}'.format(
        str(d / 'tdmp.py'),
        str(repos),
    ))
    forms = list(dsv.reader(d / 'cldf' / 'forms.csv', dicts=True))
    assert forms[0]['Profile'] == 'p1'

    _main('lexibank.format_profile {0} --clts {1} --sort --trim --augment'.format(
        str(d / 'tdmp.py'),
        str(repos),
    ))
    assert 'FREQUENCY' in (d / 'etc' / 'orthography' / 'p1.tsv').read_text(encoding='utf8')


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


def test_check_lexibank(dataset_cldf, caplog):
    _main(
        'lexibank.check_lexibank {0}'.format(str(dataset_cldf.dir / 'tdc.py')),
        log=logging.getLogger(__name__))
    warnings = [r.message for r in caplog.records if r.levelname == 'WARNING']
    print(warnings)
    assert any('Cross-concept' in w for w in warnings)


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

