from time import time

from clldutils.path import Path
from clldutils.clilib import ParserError

from pylexibank.db import Database


def get_dataset(args, name=None):
    id_ = Path(name or args.args[0]).name
    for dataset in args.cfg.datasets:
        if dataset.id == id_:
            return dataset
    raise ParserError('invalid dataset spec')  # pragma: no cover


class DatasetNotInstalledException(Exception):
    pass


def with_dataset(args, func, default_to_all=False):
    found = False
    for dataset in args.cfg.datasets:
        if (dataset.id in args.args) or (default_to_all and not args.args):
            found = True
            s = time()
            args.log.info('processing %s ...' % dataset.id)
            func(get_dataset(args, dataset.id), **vars(args))
            args.log.info('... done %s [%.1f secs]' % (dataset.id, time() - s))
    if not found:
        raise DatasetNotInstalledException("No matching dataset found!")


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
