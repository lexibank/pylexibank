# coding: utf8
from __future__ import unicode_literals, print_function, division
from time import time

from clldutils.path import Path
from clldutils.clilib import ParserError

from pylexibank.db import Database


def get_dataset(args, name=None):
    id_ = Path(name or args.args[0]).name
    for dataset in args.datasets:
        if dataset.id == id_:
            return dataset
    raise ParserError('invalid dataset spec')  # pragma: no cover


def with_dataset(args, func, default_to_all=False):
    for dataset in args.datasets:
        if (dataset.id in args.args) or (default_to_all and not args.args):
            s = time()
            args.log.info('processing %s ...' % dataset.id)
            func(get_dataset(args, dataset.id), **vars(args))
            args.log.info('... done %s [%.1f secs]' % (dataset.id, time() - s))


def _load(ds, **kw):
    db = Database(kw['db'])
    db.create(exists_ok=True)
    db.load(ds)
    db.load_concepticon_data(ds.concepticon)
    db.load_glottolog_data(ds.glottolog)


def _unload(ds, **kw):
    db = Database(kw['db'])
    db.create(exists_ok=True)
    db.unload(ds)
