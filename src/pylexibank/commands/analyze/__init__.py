# coding: utf8
from __future__ import unicode_literals, print_function, division

from clldutils.clilib import command
from clldutils.path import Manifest

from pylexibank.util import jsondump
from pylexibank.commands.analyze import transcription
from pylexibank.commands.util import with_dataset
from pylexibank.status import Workflow


@command()
def analyze(args):
    """
    Analyzes a dataset.

    lexibank analyze DATASET_ID
    """
    def _run(ds, **kw):
        if ds.status.valid_action(Workflow.analyse, kw['log']):
            if Manifest.from_dir(ds.cldf_dir) != ds.status.dirs['cldf'].manifest:
                kw['log'].error('{0} does not match checksums in {1}'.format(
                    ds.cldf_dir.as_posix(), ds.status.fname))
                return
            jsondump(
                transcription.analyze(ds),
                ds.dir.joinpath('transcription.json'),
                log=args.log)
            ds.status.register_command(Workflow.analyse, kw['cfg'], kw['log'])

    with_dataset(args, _run)
