"""
Check language specifications of lexibank datasets
"""
import functools
import collections

from cldfbench.cli_util import with_datasets
from pylexibank.cli_util import add_dataset_spec, warning


def register(parser):  # pylint: disable=C0116
    add_dataset_spec(parser, multiple=True)


def check(ds, args, warnings=None):
    """Check a single dataset."""
    warn = functools.partial(warning, args, dataset=ds, warnings=warnings)

    args.log.info('checking %s - languages', ds)
    cldf = ds.cldf_reader()

    cols_with_values = collections.Counter()  # used for check on empty columns
    row = None
    for row in cldf['LanguageTable']:
        cols_with_values.update([key for key in row if row[key]])

    # check for empty columns
    if row:
        for col in row:
            if not cols_with_values.get(col):
                warn(f'Column {col} in LanguageTable is completely empty')


def run(args):  # pylint: disable=C0116
    with_datasets(args, check)  # pragma: no cover
