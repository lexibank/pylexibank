# coding: utf8
from __future__ import unicode_literals, print_function, division


def test_with_dataset(mocker, capsys, dataset):
    from pylexibank.commands.util import with_dataset

    def func(*args, **kw):
        print('hello!')

    with_dataset(mocker.Mock(datasets=[dataset], args=['test_dataset']), func)
    out, err = capsys.readouterr()
    assert 'processing' in out
    assert 'hello!' in out
    assert 'done' in out


def test_db(dataset):
    from pylexibank.commands.util import _load, _unload

    db = dataset.dir / 'db.sqlite'
    _load(dataset, db=db)
    _unload(dataset, db=db)


def test_workflow(repos, mocker, capsys, dataset, tmppath):
    from pylexibank.commands.analyze import analyze
    from pylexibank.commands.report import report
    from pylexibank.commands.misc import ls, bib

    def _args(*args):
        return mocker.Mock(
            datasets=[dataset],
            cfg={'paths': {'lexibank': repos.as_posix()}},
            log=mocker.Mock(),
            db=tmppath / 'db.sqlite',
            verbose=True,
            args=list(args))

    dataset._download(**vars(_args('test_dataset')))
    out, err = capsys.readouterr()

    dataset._install(**vars(_args('test_dataset')))
    out, err = capsys.readouterr()

    ls(_args('test_dataset', 'license'))
    out, err = capsys.readouterr()

    analyze(dataset, **vars(_args('test_dataset')))
    out, err = capsys.readouterr()

    assert not dataset.stats
    report(dataset, **vars(_args('test_dataset')))
    out, err = capsys.readouterr()
    assert dataset.stats

    bib(_args())
    assert repos.joinpath('lexibank.bib').exists()
    out, err = capsys.readouterr()

    dataset.cldf_dir.joinpath('tmp').mkdir()
    dataset._clean()
    assert not dataset.cldf_dir.joinpath('tmp').exists()
