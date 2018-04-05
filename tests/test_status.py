# coding: utf8
from __future__ import unicode_literals, print_function, division

from clldutils.path import write_text


def test_Command():
    from pylexibank.status import Command

    cmd = Command.from_name('install')
    cmd.update({'paths': {}})
    assert cmd.workflow.name == 'install'
    assert cmd == Command(**cmd.asdict())
    last_run = cmd.last_run
    cmd.update({'paths': {}})
    assert cmd.last_run > last_run


def test_Status(mocker, tmppath):
    from pylexibank.status import Status, Workflow

    st = Status(tmppath / 'status.json')
    st.register_command('download', {'paths': {}}, mocker.Mock())
    assert 'download' in '{0}'.format(st)
    write_text(tmppath / 'test.txt', 'text')
    st.register_dir(tmppath)
    st2 = Status.from_file(tmppath / 'status.json')
    assert st2 == st
    st2.register_dir(tmppath)
    st.register_command('install', {'paths': {}}, mocker.Mock())
    assert st2 != st

    st.register_command('install', {'paths': {}}, mocker.Mock())
    assert st.status > Workflow.download
    st.register_command('download', {'paths': {}}, mocker.Mock())
    assert st.status == Workflow.download
    assert not st.valid_action(Workflow.report, mocker.Mock())
