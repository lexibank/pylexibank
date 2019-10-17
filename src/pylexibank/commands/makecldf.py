"""
Run makecldf command of a dataset
"""
from cldfbench.cli_util import with_dataset, get_dataset

from pylexibank.cli_util import add_catalogs, add_dataset_spec


def register(parser):
    add_dataset_spec(parser)
    add_catalogs(parser)
    parser.add_argument('--verbose', action='store_true')


def run(args):
    dataset = get_dataset(args)
    dataset.concepticon = args.concepticon.api
    dataset.glottolog = args.glottolog.api
    with_dataset(args, 'makecldf', dataset=dataset)
