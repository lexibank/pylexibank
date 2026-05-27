"""
Functionality used in pylexibank commands.
"""
import argparse

from cldfbench import cli_util
from termcolor import colored

from pylexibank.util import ENTRY_POINT


def read_forms(dataset):
    """Read the lexibank FormTable."""
    return list(dataset.get_lexibank_wordlist().iter_rows(
        'FormTable', 'id', 'form', 'value', 'segments', 'languageReference', 'parameterReference'))


def add_dataset_spec(parser: argparse.ArgumentParser, **kw):
    """Add a dataset spec that also knows the lexibank dataset entry-point."""
    kw.setdefault('ep', ENTRY_POINT)
    return cli_util.add_dataset_spec(parser, **kw)


def add_catalogs(parser: argparse.ArgumentParser, with_clts: bool = False):
    """Add the relevant reference catalogs for Lexibank."""
    cli_util.add_catalog_spec(parser, 'glottolog')
    cli_util.add_catalog_spec(parser, 'concepticon')
    if with_clts:
        cli_util.add_catalog_spec(parser, 'clts')


def add_overwrite_profile_flag(parser: argparse.ArgumentParser):
    """Allows opting in to overwriting existing data."""
    parser.add_argument(
        '-f', '--force',
        action='store_true',
        help='Overwrite existing profile',
        default=False)


def warning(args, msg, dataset=None, warnings=None):
    """Emit a warning."""
    if dataset:
        msg = f"{colored(dataset.id, 'blue', attrs=['bold'])}: {msg}"
    args.log.warning(msg)
    if warnings is not None:
        warnings.append(msg)
