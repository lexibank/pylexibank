import pathlib

from cldfbench import cli_util

from pylexibank import ENTRY_POINT
from pylexibank.db import Database


def add_dataset_spec(parser, **kw):
    kw.setdefault('ep', ENTRY_POINT)
    return cli_util.add_dataset_spec(parser, **kw)


def add_db(parser):
    parser.add_argument(
        '--db',
        help='path to SQLite db file',
        type=pathlib.Path,
        default=pathlib.Path.cwd() / 'lexibank.sqlite')


def get_db(args):
    db = Database(args.db)
    db.create(exists_ok=True)
    return db


def add_catalogs(parser, with_clts=False):
    cli_util.add_catalog_spec(parser, 'glottolog')
    cli_util.add_catalog_spec(parser, 'concepticon')
    if with_clts:
        cli_util.add_catalog_spec(parser, 'clts')
