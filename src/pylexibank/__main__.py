"""
Main command line interface of the pylexibank package.

Like programs such as git, this cli splits its functionality into sub-commands
(see e.g. https://docs.python.org/2/library/argparse.html#sub-commands).
The rationale behind this is that while a lot of different tasks may be
triggered using this cli, most of them require common configuration.

The basic invocation looks like

    lexibank [OPTIONS] <command> [args]

"""
from __future__ import unicode_literals, division, print_function
import sys
import os
import argparse
import readline
import glob
import pkg_resources

from termcolor import colored
from appdirs import user_config_dir
from six.moves import input
from clldutils.inifile import INI
from clldutils.clilib import ArgumentParserWithLogging
from clldutils.path import Path

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


def configure():  # pragma: no cover
    """
    Configure lexibank.

    :return: a pair (config, logger)
    """
    cfgpath = Path(user_config_dir(pylexibank.__name__)).joinpath('config.ini')
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
        cfg = INI()
        cfg['paths'] = {k: get_path(src) for k, src in REPOS}
        cfg.write(cfgpath)
        print("""
Configuration has been written to:
{0}
You may edit this file to adapt to changes in your system or to reconfigure settings
such as the logging level.""".format(cfgpath.resolve()))
    else:
        cfg = INI.from_file(cfgpath)

    glottolog = Glottolog(cfg['paths']['glottolog'])
    concepticon = Concepticon(cfg['paths']['concepticon'])
    datasets = sorted(
        iter_datasets(glottolog=glottolog, concepticon=concepticon, verbose=True),
        key=lambda d: d.id)
    return cfg, datasets


def main():  # pragma: no cover
    cfg, datasets = configure()
    parser = ArgumentParserWithLogging(pylexibank.__name__)
    parser.add_argument('--cfg', help=argparse.SUPPRESS, default=cfg)
    parser.add_argument('--datasets', help=argparse.SUPPRESS, default=datasets)
    parser.add_argument(
        '--db',
        help=argparse.SUPPRESS,
        default=os.path.join(os.getcwd(), 'lexibank.sqlite'))
    sys.exit(parser.main())
