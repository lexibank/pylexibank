"""
Check forms against a dataset's orthography profile.
"""
from clldutils.clilib import Table, add_format
from cldfbench.cli_util import with_dataset
from pylexibank.cli_util import add_dataset_spec, read_forms


def register(parser):  # pylint: disable=C0116
    add_dataset_spec(parser)
    add_format(parser, default='pipe')


def run(args):  # pylint: disable=C0116
    with_dataset(args, check_segments)


def check_segments(dataset, args):
    """Check a single dataset."""
    with Table(args, 'Type', 'ID', 'Value', 'Form', 'Graphemes', 'Segments') as table:
        for row in sorted(read_forms(dataset), key=lambda r: r['id']):
            etype, tokens = None, " ".join(row['segments'] or [])
            if tokens:
                if any(x in y for x, y in [
                    (tokens[0], ['+', '_', '#']),
                    (tokens[-1], ['+', '_', '#']),
                    ('+ +', tokens),
                    ('_ _', tokens),
                    ('#', tokens),
                    ('_', tokens),
                ]):
                    etype = 1
            else:
                etype = 2  # pragma: no cover
            if etype:
                table.append(
                    [etype, row['id'], row['value'], row['form'], row['Graphemes'] or '', tokens])
