import shlex
import logging
import argparse

import pytest

from csvw import dsv
from clldutils import jsonlib
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
    kw.setdefault('log', logging.getLogger(__name__))
    main(['--no-config'] + shlex.split(cmd), **kw)


@pytest.mark.filterwarnings("ignore:distutils Version:DeprecationWarning")
def test_makecldf_concepticon_concepts(repos):
    d = repos / 'datasets' / 'test_dataset_concepticon_concepts'
    _main('lexibank.makecldf {0} --glottolog {1} --concepticon {1} --clts {1}'.format(
        d / 'tdcc.py', repos))
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


def test_makecldf(repos, dataset, dataset_cldf, dataset_no_cognates, sndcmp, capsys, tmp_path):
    _main('lexibank.makecldf {0} --glottolog {1} --concepticon {1} --clts {1}'.format(
        str(dataset.dir / 'td.py'),
        str(repos),
    ))
    assert 'Papunesia' in dataset.cldf_dir.joinpath('languages.csv').read_text(encoding='utf8')
    # Metadata for Zenodo is merged if this makes sense:
    assert len(jsonlib.load(dataset.dir / '.zenodo.json')['communities']) == 3

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

    _main('lexibank.makecldf {0} --glottolog {1} --concepticon {1} --clts {1}'.format(
        str(dataset_cldf.dir / 'tdc.py'),
        str(repos),
    ))
    capout = capsys.readouterr().out
    assert 'The dataset has no sources' not in capout

    _main('lexibank.makecldf {0} --glottolog {1} --concepticon {1} --clts {1}'.format(
        str(dataset_no_cognates.dir / 'tdn.py'),
        str(repos),
    ))
    assert not dataset_no_cognates.cldf_dir.joinpath('cognates.csv').exists()
    _main('lexibank.load --db {3} {0} --glottolog {1} --concepticon {2}'.format(
        str(dataset_no_cognates.dir / 'tdn.py'),
        str(repos),
        str(repos),
        str(tmp_path / 'db'),
    ))


def test_check(dataset_cldf, caplog):
    _main('lexibank.check {0}'.format(str(dataset_cldf.dir / 'tdc.py')),
          log=logging.getLogger(__name__))
    assert [r for r in caplog.records if 'CONTRIBUTORS.md' in r.message]


def test_check_lexibank(dataset_cldf, caplog):
    _main(
        'lexibank.check_lexibank {0}'.format(str(dataset_cldf.dir / 'tdc.py')),
        log=logging.getLogger(__name__))
    warnings = [r.message for r in caplog.records if r.levelname == 'WARNING']
    print(warnings)
    assert any('Cross-concept' in w for w in warnings)


def test_ls(repos, tmp_path, dataset):
    _main('lexibank.load --db {3} {0} --glottolog {1} --concepticon {2}'.format(
        dataset.dir / 'td.py', repos, repos, tmp_path / 'db'))
    _main('lexibank.ls {0} --all --db {1}'.format(dataset.dir / 'td.py', tmp_path / 'db'))
    _main('lexibank.unload --db {1} {0}'.format(dataset.dir / 'td.py', tmp_path / 'db'))


def test_db(tmp_path, mocker):
    mocker.patch('pylexibank.commands.db.subprocess', mocker.Mock(return_value=0))
    _main('lexibank.db --db {0}'.format(tmp_path / 'db'))


def test_check_phonotactics(dataset, capsys):
    _main('lexibank.check_phonotactics {0}'.format(str(dataset.dir / 'td.py')))
    out, _ = capsys.readouterr()
    assert out.strip() == """| Type | ID | Value | Form | Graphemes | Segments |
|-------:|:---------------|:--------|:-------|:------------|:------------|
| 1 | lang1-param1-1 | a b; c | a b | | a _ b |
| 1 | lang2-param2-2 | a~b-c | ab | | + a + + b + |"""


def test_consonant_clusters(dataset, repos, caplog, capsys):
    d = repos / 'datasets' / 'test_dataset_multi_profile_with_cldf'
    _main('lexibank.consonant_clusters {0} --clts {1}'.format(str(d / 'tdmpcldf.py'), repos))
    out, _ = capsys.readouterr()

    assert out.strip() == """| Language_ID | Length | Cluster | Words |
|:--------------|---------:|:----------------------|:--------|
| lang1 | 3 | ɡ̤ː ɡ̤ː b | axdou |
| lang1 | 6 | ɡ̤ː ɡ̤ː b dʱʷ dʱʷ dʱʷ | axdou |"""


def test_check_profile(dataset, repos, caplog, capsys):
    _main('lexibank.check_profile {0} --clts {1}'.format(str(dataset.dir / 'td.py'), repos))
    assert len(caplog.records) == 2
    d = repos / 'datasets' / 'test_dataset_multi_profile_with_cldf'
    _main('lexibank.check_profile {0} --clts {1}'.format(str(d / 'tdmpcldf.py'), repos))
    assert len(caplog.records) == 4
    out, _ = capsys.readouterr()
    assert all(w in out for w in 'modified generated slashed unknown missing'.split())


def test_init_profile(dataset, repos):
    _main('lexibank.init_profile {0} --clts {1} -f --context --merge-vowels'.format(
        str(dataset.dir / 'td.py'), repos))
    with pytest.raises(SystemExit):
        _main('lexibank.init_profile {0} --clts {1}'.format(str(dataset.dir / 'td.py'), repos))


def test_language_profiles(dataset_cldf, repos):
    with pytest.raises(ValueError):
        _main('lexibank.language_profiles {0}'.format(str(dataset_cldf.dir / 'tdc.py')))
    d = repos / 'datasets' / 'test_dataset_cldf_capitalisation'
    _main('lexibank.language_profiles {0}'.format(str(d / 'tdc.py')))


def test_readme(dataset, repos):
    _main(
        'lexibank.readme {0} --glottolog {1}'.format(str(dataset.dir / 'td.py'), repos))
    assert dataset.dir.joinpath('FORMS.md').exists()
    assert '# Contributors' in dataset.dir.joinpath('README.md').read_text(encoding='utf8')


def test_new(tmp_path, mocker):
    mocker.patch('cldfbench.metadata.input', mocker.Mock(return_value='abc'))
    _main('new --template lexibank_simple --out ' + str(tmp_path))
    assert tmp_path.joinpath('abc', 'CONTRIBUTORS.md').exists()

    mocker.patch('cldfbench.metadata.input', mocker.Mock(return_value='cde'))
    _main('new --template lexibank_combined --out ' + str(tmp_path))
    assert '{{' not in tmp_path.joinpath('cde', 'lexibank_cde.py').read_text(encoding='utf8')

