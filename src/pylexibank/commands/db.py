# coding: utf8
from __future__ import unicode_literals, print_function, division

from clldutils.clilib import command
from clldutils.markup import Table
from pyglottolog.api import Glottolog
from pyconcepticon.api import Concepticon

from pylexibank.db import Database


@command()
def dbcreate(args):
    db = Database(getattr(args, 'db', None))
    db.create()
    for ds in args.datasets:
        if ds.cldf_dir.joinpath('forms.csv').exists():
            args.log.info('loading {0}'.format(ds))
            db.load(ds.cldf.wl)
    args.log.info('db created at {0}'.format(db.fname))


@command()
def dbload(args):
    db = Database(getattr(args, 'db', None))
    for name, api_cls in [('glottolog', Glottolog), ('concepticon', Concepticon)]:
        if (not args.args) or (name in args.args):
            getattr(db, 'load_{0}_data'.format(name))(api_cls(args.cfg['paths'][name]))


@command()
def dbquery(args):
    db = Database()
    args.log.info(db.fname)
    args.log.info(args.args[0])
    with db.connection() as conn:
        cu = conn.cursor()
        cu.execute(args.args[0])
        header = [desc[0] for desc in cu.description]
        rows = [r for r in cu.fetchall()]
    table = Table(*header)
    table.extend(rows)
    print(table.render(condensed=False, verbose=True))
