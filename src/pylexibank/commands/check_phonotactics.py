"""
Check forms against a dataset's orthography profile.
"""
from clldutils.clilib import Table, add_format
from cldfbench.cli_util import with_dataset
from pylexibank.cli_util import add_dataset_spec


def register(parser):
    add_dataset_spec(parser)
    add_format(parser, default='pipe')


def run(args):
    with_dataset(args, check_segments)


def check_segments(dataset, args):
    with Table(args, 'Type', 'ID', 'Value', 'Form', 'Graphemes', 'Segments') as table:
        for row in sorted(
                dataset.cldf_dir.read_csv('forms.csv', dicts=True), key=lambda r: r['ID']):
            etype, tokens = None, row['Segments']
            tkl = row['Segments'].split()
            if tkl:
                if any(x in y for x, y in [
                    (tkl[0], ['+', '_', '#']),
                    (tkl[-1], ['+', '_', '#']),
                    ('+ +', tokens),
                    ('_ _', tokens),
                    ('#', tokens),
                    ('_', tokens),
                ]):
                    etype = 1
            else:
                etype = 2  # pragma: no cover
            if etype:
                table.append([
                    etype, row['ID'], row['Value'], row['Form'], row['Graphemes'], row['Segments']])
