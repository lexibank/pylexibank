"""
Run all checks
"""
from cldfbench.cli_util import with_datasets, add_catalog_spec
from pylexibank.cli_util import add_dataset_spec

from pylexibank.commands.check_languages import check as check_languages
from pylexibank.commands.check_lexibank import check as check_lexibank

CHECKERS = [check_languages, check_lexibank]


def register(parser):
    add_dataset_spec(parser, multiple=True)
    add_catalog_spec(parser, 'glottolog')


def check(ds, args):
    for checker in CHECKERS:
        checker(ds, args)


def run(args):
    with_datasets(args, check)
