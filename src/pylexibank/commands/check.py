"""
Run all checks
"""
from cldfbench.cli_util import with_datasets
from pylexibank.cli_util import add_dataset_spec

from pylexibank.commands.check_languages import check as check_languages
from pylexibank.commands.check_lexibank import check as check_lexibank

CHECKERS = [check_languages, check_lexibank]


def register(parser):  # pylint: disable=C0116
    add_dataset_spec(parser, multiple=True)


def check(ds, args):
    """Run checks for one dataset."""
    for checker in CHECKERS:
        checker(ds, args, warnings=args.warnings)


def run(args):  # pylint: disable=C0116
    args.warnings = []
    with_datasets(args, check)
    if args.warnings:
        args.log.warning('%s warnings issued', len(args.warnings))
        return 2
    args.log.info('OK')  # pragma: no cover
    return 0  # pragma: no cover
