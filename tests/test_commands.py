# coding: utf8
from __future__ import unicode_literals, print_function, division


def test_workflow(repos, mocker, capsys, dataset, tmppath):
    from pylexibank.commands.analyze import analyze
    from pylexibank.commands.report import report
    from pylexibank.commands.misc import ls, bib
    from pylexibank.commands.db import dbcreate

    def _args(*args):
        return mocker.Mock(
            datasets=[dataset],
            cfg={'paths': {'lexibank': repos.as_posix()}},
            log=mocker.Mock(),
            db=tmppath / 'db.sqlite',
            args=list(args))

    dataset._download(**vars(_args('test_dataset')))
    out, err = capsys.readouterr()

    dataset._install(**vars(_args('test_dataset')))
    out, err = capsys.readouterr()

    dbcreate(_args('test_dataset'))
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
