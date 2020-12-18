"""
Check forms against a dataset's orthography profile.
"""
from cldfbench.cli_util import with_dataset
from pylexibank.cli_util import add_dataset_spec
from tabulate import tabulate


def register(parser):
    add_dataset_spec(parser)


def run(args):
    with_dataset(args, check_segments)


def check_segments(dataset, args):
    table = []
    for row in dataset.cldf_dir.read_csv('forms.csv', dicts=True):
        tokens = row['Segments']
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
                table += [[
                    1,
                    row['ID'],
                    row['Value'],
                    row['Form'],
                    row['Graphemes'],
                    row['Segments']]]
        else:
            table += [[
                2, row['ID'], row['Value'], row['Form'], row['Graphemes'],
                row['Segments']]]
    print(tabulate(
        sorted(table, key=lambda x: (x[1], x[0])),
        headers=['Type', 'ID', 'Value', 'Form', 'Graphemes', 'Segments'],
        tablefmt='pipe'))
