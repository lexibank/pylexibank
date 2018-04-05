# coding: utf8
from __future__ import unicode_literals, print_function, division
from time import time

from clldutils.path import Path
from clldutils.clilib import ParserError


def get_dataset(args, name=None):
    id_ = Path(name or args.args[0]).name
    for dataset in args.datasets:
        if dataset.id == id_:
            return dataset
    raise ParserError('invalid dataset spec')  # pragma: no cover


def with_dataset(args, func):
    process, first = True, None
    if args.args:
        if 'start-with' == args.args[0]:  # pragma: no cover
            first = args.args[1]
            process = False
        else:
            func(get_dataset(args), **vars(args))
            return

    for dataset in args.datasets:
        if not process:  # pragma: no cover
            process = dataset.id == first
        if process:
            s = time()
            print('processing %s ...' % dataset.id)
            func(get_dataset(args, dataset.id), **vars(args))
            print('... done %s [%.1f secs]' % (dataset.id, time() - s))
