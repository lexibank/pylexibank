"""
Check phonotactics of segmented data.
"""
import collections

from cldfbench.cli_util import with_dataset
from clldutils import markup

from pylexibank.cli_util import add_dataset_spec


def register(parser):
    add_dataset_spec(parser)


def run(args):
    with_dataset(args, check_phonotactics)


def table(problems):
    table_ = markup.Table('No', 'ID', 'Form', 'Segments')
    for i, (a, b, c) in enumerate(problems, start=1):
        table_.append((i, a, b, c))
    return table_.render(tablefmt='pipe')


def check_phonotactics(dataset, args):
    problems = collections.defaultdict(list)
    for row in dataset.cldf_dir.read_csv('forms.csv', dicts=True):
        tokens = row['Segments'].split()
        # trailing plusses
        if tokens[-1] == '+':
            problems['+$'] += [(row['ID'], row['Form'], row['Segments'])]
        if tokens[0] == '+':
            problems['^+'] += [(row['ID'], row['Form'], row['Segments'])]
        if '+ +' in row['Segments']:
            problems['++'] += [(row['ID'], row['Form'], row['Segments'])]
    if not problems:  # pragma: no cover
        print('Found no errors.')
        return
    if '+$' in problems:
        print('# Segments end in +:')
        print(table(problems['+$']))
    if '^+' in problems:
        print('# Segments start with +:')
        print(table(problems['^+']))
    if '++' in problems:
        print('# Segments have consecutive +:')
        print(table(problems['++']))
