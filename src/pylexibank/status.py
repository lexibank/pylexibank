# coding: utf8
from __future__ import unicode_literals, print_function, division
from datetime import datetime
import sys
from subprocess import check_output

from termcolor import colored
import attr
from clldutils import jsonlib
from clldutils.path import git_describe, Manifest, Path
from clldutils.misc import UnicodeMixin
from clldutils.declenum import DeclEnum


class Workflow(DeclEnum):
    init = 0, 'initialized'
    download = 1, 'downloaded'
    install = 2, 'installed'
    analyse = 3, 'analysed'
    report = 4, 'summarised'


class Serializable(object):
    def asdict(self):
        return attr.asdict(self)


def pip_freeze():
    try:
        return check_output(['pip', 'freeze']).decode('utf8')
    except:
        return ''


@attr.s
class System(Serializable):
    repos = attr.ib()
    requirements = attr.ib(default=attr.Factory(pip_freeze))
    python = attr.ib(default=sys.version)

    @classmethod
    def from_cfg(cls, cfg):
        return cls(repos={k: git_describe(v) for k, v in cfg['paths'].items()})


@attr.s
class Command(Serializable):
    workflow = attr.ib(convert=Workflow.get)
    system = attr.ib(convert=lambda s: s if isinstance(s, System) else System(**s))
    last_run = attr.ib(
        convert=lambda d: d if isinstance(d, datetime)
        else datetime.strptime(d, '%Y-%m-%dT%H:%M:%S.%f'),
        default=attr.Factory(lambda: datetime.utcnow()))

    @property
    def name(self):
        return self.workflow.name

    @classmethod
    def from_name(cls, name):
        return cls(workflow=name, system=System(None, None, None))

    def update(self, cfg):
        self.last_run = datetime.utcnow()
        self.system = System.from_cfg(cfg)

    def asdict(self):
        return dict(
            workflow=self.workflow.name,
            system=self.system.asdict(),
            last_run=self.last_run.isoformat())


@attr.s
class Dir(Serializable):
    name = attr.ib()
    manifest = attr.ib()

    def update(self, d):
        assert d.name == self.name
        self.manifest = Manifest.from_dir(d)

    @classmethod
    def from_name(cls, name):
        return cls(name, {})


@attr.s
class Status(UnicodeMixin):
    fname = attr.ib(default=Path('status.json'), convert=Path)
    commands = attr.ib(default=attr.Factory(dict))
    dirs = attr.ib(default=attr.Factory(dict))

    def __unicode__(self):
        return '{0}\n\nHistory:\n'.format(
            self.status.description,
            '\n'.join('- {0} {1}'.format(cm.name, cm.last_run)
                      for cm in self.commands.values()))

    @property
    def status(self):
        return max(cmd.workflow for cmd in self.commands.values()) \
            if self.commands else Workflow.init

    def asdict(self):
        return {
            'fname': self.fname.as_posix(),
            'commands': [cmd.asdict() for cmd in self.commands.values()],
            'dirs': [d.asdict() for d in self.dirs.values()]}

    def valid_action(self, wf, log):
        if wf.value <= self.status.value + 1:
            return True
        log.error('{0} is not allowed for dataset in status {1}'.format(
            colored(repr(wf), 'red'), colored(self.status.description, 'red')))
        return False

    def register_command(self, name, cfg, log):
        wf = Workflow.get(name)
        cmd = self.commands.setdefault(wf.name, Command.from_name(wf.name))
        cmd.update(cfg)
        self.commands = {n: cmd for n, cmd in self.commands.items() if cmd.workflow <= wf}
        self.write()
        log.info('{0} run at {1}; new status: {2}'.format(
            colored(repr(wf), 'blue'), cmd.last_run, colored(wf.description, 'blue')))

    def register_dir(self, dir_):
        d = self.dirs.setdefault(dir_.name, Dir.from_name(dir_.name))
        d.update(dir_)
        self.write()

    @classmethod
    def from_file(cls, fname):
        data = jsonlib.load(fname) if fname.exists() else {}
        return cls(
            fname,
            {c.name: c for c in [Command(**cmd) for cmd in data.get('commands', [])]},
            {d.name: d for d in [Dir(**_d) for _d in data.get('dirs', [])]})

    def write(self):
        jsonlib.dump(self.asdict(), self.fname, indent=4)
