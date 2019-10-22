"""
Load dataset(s) into the lexibank SQLite database.
"""
from cldfbench.cli_util import with_datasets

from pylexibank.cli_util import add_db, add_catalogs, get_db, add_dataset_spec


def register(parser):
    add_db(parser)
    add_dataset_spec(parser, multiple=True)
    add_catalogs(parser)


def run(args):
    db = get_db(args)
    with_datasets(args, db.load)
    db.load_concepticon_data(args.concepticon.api)
    db.load_glottolog_data(args.glottolog.api)
