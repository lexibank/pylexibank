# coding: utf8
from __future__ import unicode_literals, print_function, division

from clldutils.clilib import command

from pylexibank.util import jsondump
from pylexibank.commands.analyze import transcription
from pylexibank.commands.util import with_dataset


@command()
def analyze(args):
    """
    Analyzes a dataset.

    lexibank analyze DATASET_ID
    """
    def _run(ds, **kw):
        jsondump(
            transcription.analyze(ds),
            ds.dir.joinpath('transcription.json'),
            log=args.log)

    with_dataset(args, _run)
