import os
import contextlib

from clldutils.inifile import INI

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

    new_dataset(mocker.Mock(args=[str(tmpdir)]))
    assert tmpdir.join('abc').check()

    with chdir(str(tmpdir / 'abc')):
        exec(tmpdir.join('abc', 'lexibank_abc.py').read_binary(), dict(__file__='a'))
        with pytest.raises(SystemExit):
            exec(tmpdir.join('abc', 'setup.py').read_binary())


@pytest.fixture
def configmaker(tmpdir):
    def make(glottolog, concepticon):
        ini = INI()
        ini.read_dict({'paths': {'concepticon': concepticon, 'glottolog': glottolog}})
        p = str(tmpdir.join('config.ini'))
        ini.write(p)
        return p
    return make


def test_configure_first_run(tmpdir, capsys, mocker, repos):
    mocker.patch('pylexibank.__main__.input', mocker.Mock(return_value=str(repos)))
    __main__.configure(str(tmpdir.join('d', 'cfg.ini')))
    out, _ = capsys.readouterr()
    assert 'Configuration has been written' in out


def test_configure(configmaker, repos):
    with pytest.raises(__main__.ParserError):
        __main__.configure(configmaker('x', 'y'))
    with pytest.raises(__main__.ParserError):
        __main__.configure(configmaker(str(repos), 'y'))
