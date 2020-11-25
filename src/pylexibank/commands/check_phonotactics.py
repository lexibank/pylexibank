"""
Check forms against a dataset's orthography profile.
"""
from cldfbench.cli_util import with_dataset, add_catalog_spec
from pylexibank.cli_util import add_dataset_spec
from tabulate import tabulate

def register(parser):
    add_dataset_spec(parser)


def run(args):
    with_dataset(args, check_segments)


def check_segments(dataset, args):
    problems, visited = set(), set()
    table = []
    for row in dataset.cldf_dir.read_csv('forms.csv', dicts=True):
        tokens = row['Segments']
        tkl = row['Segments'].split()
        if tkl:
            if (
                    tkl[0] in ['+', '_', '#'] or 
                    tkl[-1] in ['+', '_', '#'] or 
                    '+ +' in tokens or 
                    '_ _' in tokens or 
                    '#' in tokens or
                    '_' in tokens
                    ):
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
