import os
import contextlib

import pytest

from pylexibank import __main__


@contextlib.contextmanager
def chdir(d):
    cwd = os.getcwd()
    os.chdir(d)
    yield d
    os.chdir(cwd)


def test_new_dataset(tmpdir, mocker):
    from pylexibank.commands.misc import new_dataset

    mocker.patch('pylexibank.commands.misc.input', mocker.Mock(return_value='abc'))
    new_dataset(mocker.Mock(args=[str(tmpdir), 'newid']))
    assert tmpdir.join('newid').check()

    with pytest.raises(ValueError):
        new_dataset(mocker.Mock(args=[str(tmpdir), 'newid']))

    new_dataset(mocker.Mock(args=[str(tmpdir)]))
    assert tmpdir.join('abc').check()

    with chdir(str(tmpdir / 'abc')):
        exec(tmpdir.join('abc', 'lexibank_abc.py').read_binary(), dict(__file__='a'))
        with pytest.raises(SystemExit):
            exec(tmpdir.join('abc', 'setup.py').read_binary())
