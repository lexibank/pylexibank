"""
Check forms against a dataset's orthography profile.
"""
from cldfbench.cli_util import with_dataset, add_catalog_spec

from pylexibank.cli_util import add_dataset_spec


def register(parser):
    add_dataset_spec(parser)
    add_catalog_spec(parser, 'clts')


def run(args):
    with_dataset(args, check_profile)


def check_profile(dataset, args):
    problems, visited = set(), set()
    for row in dataset.cldf_dir.read_csv('forms.csv', dicts=True):
        tokens = dataset.tokenizer({}, row['Form'], column='IPA') if \
            dataset.tokenizer else row['Segments'].split()
        for tk in set(tokens):
            if tk not in visited:
                visited.add(tk)
                if args.clts.api.bipa[tk].type == 'unknownsound':
                    problems.add(tk)
                    print('{0:5}\t{1:20}\t{2}'.format(tk, ' '.join(tokens), row['Form']))
    print('Found {0} errors in {1} segments.'.format(len(problems), len(visited)))
