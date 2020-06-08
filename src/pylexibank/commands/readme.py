"""
Write dataset metadata to a README.md in the dataset's directory.
"""
from cldfbench.cli_util import add_dataset_spec, with_datasets, add_catalog_spec


def register(parser):
    add_dataset_spec(parser, multiple=True)
    add_catalog_spec(parser, 'glottolog')
    parser.add_argument('--dev', action='store_true', default=False)


def run(args):
    with_datasets(args, 'readme')
