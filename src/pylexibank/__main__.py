"""
Main command line interface of the pylexibank package.

Like programs such as git, this cli splits its functionality into sub-commands
(see e.g. https://docs.python.org/2/library/argparse.html#sub-commands).
The rationale behind this is that while a lot of different tasks may be
triggered using this cli, most of them require common configuration.

The basic invocation looks like

    lexibank [OPTIONS] <command> [args]

"""
import sys
import os
import argparse
import readline
import glob

from termcolor import colored
from appdirs import user_config_dir
from clldutils.inifile import INI
from clldutils.clilib import ArgumentParserWithLogging, ParserError
from clldutils.path import Path
from clldutils.misc import lazyproperty

import pylexibank
from pylexibank.dataset import iter_datasets
from pylexibank.glottolog import Glottolog
from pylexibank.concepticon import Concepticon
import pylexibank.commands
assert pylexibank.commands

REPOS = [
    ('glottolog', 'clld/glottolog'),
    ('concepticon', 'clld/concepticon-data'),
]


# We want to provide tab-completion when the user is asked to provide local paths to
# repository clones.
def complete_dir(text, state):  # pragma: no cover
    if os.path.isdir(text) and not text.endswith(os.sep):
        text += os.sep
    return ([p for p in glob.glob(text + '*') if os.path.isdir(p)] + [None])[state]


readline.parse_and_bind("tab: complete")
readline.set_completer_delims('\t')
readline.set_completer(complete_dir)


def get_path(src):  # pragma: no cover
    """
    Prompts the user to input a local path.

    :param src: github repository name
    :return: Absolute local path
    """
    res = None
    while not res:
        if res is False:
            print(colored('You must provide a path to an existing directory!', 'red'))
        print('You need a local clone or release of (a fork of) '
              'https://github.com/{0}'.format(src))
        res = input(colored('Local path to {0}: '.format(src), 'green', attrs=['blink']))
        if res and Path(res).exists():
            return Path(res).resolve()
        res = False


class Config(INI):
    @lazyproperty
    def concepticon(self):
        return Concepticon(self['paths']['concepticon'])

    @lazyproperty
    def glottolog(self):
        return Glottolog(self['paths']['glottolog'])

    @lazyproperty
    def datasets(self):
        return sorted(
            iter_datasets(glottolog=self.glottolog, concepticon=self.concepticon, verbose=True),
            key=lambda d: d.id)


def configure(cfgpath=None):
    """
    Configure lexibank.

    :return: a pair (config, logger)
    """
    cfgpath = Path(cfgpath) \
        if cfgpath else Path(user_config_dir(pylexibank.__name__)) / 'config.ini'
    if not cfgpath.exists():
        print("""
{0}

You seem to be running lexibank for the first time.
Your system configuration will now be written to a config file to be used
whenever lexibank is run lateron.
""".format(
            colored('Welcome to lexibank!', 'blue', attrs=['bold', 'reverse'])))
        if not cfgpath.parent.exists():
            cfgpath.parent.mkdir(parents=True)
        cfg = Config()
        cfg['paths'] = {k: get_path(src) for k, src in REPOS}
        cfg.write(cfgpath)
        print("""
Configuration has been written to:
{0}
You may edit this file to adapt to changes in your system or to reconfigure settings
such as the logging level.""".format(cfgpath.resolve()))
    else:
        cfg = Config.from_file(cfgpath)

    try:
        cfg.glottolog
    except (FileNotFoundError, ValueError):
        raise ParserError('Misconfigured Glottolog path in {0}'.format(cfgpath))
    if not Path(cfg['paths']['concepticon']).exists():
        raise ParserError('Misconfigured Concepticon path in {0}'.format(cfgpath))

    # Print the configuration directory for reference:
    print("Using configuration file at:")
    print(str(cfgpath) + '\n')
    return cfg


def main():  # pragma: no cover
    cfg = configure()
    parser = ArgumentParserWithLogging(pylexibank.__name__)
    parser.add_argument('--cfg', help=argparse.SUPPRESS, default=cfg)
    parser.add_argument(
        '--db',
        help='path to SQLite db file',
        default=os.path.join(os.getcwd(), 'lexibank.sqlite'))
    sys.exit(parser.main())
