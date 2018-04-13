# coding: utf8
from __future__ import unicode_literals, print_function, division

from clldutils.clilib import command
from clldutils import jsonlib

from pylexibank.util import textdump
from pylexibank.commands.util import with_dataset
from pylexibank.commands.report import readme
from pylexibank.commands.report import transcription


@command()
def report(args):
    """Create a README.md file listing the contents of a dataset

    lexibank report [DATASET_ID]
    """
    def _run(ds, **kw):
        tr = jsonlib.load(ds.dir.joinpath('transcription.json'))
        textdump(
            transcription.report(tr, **kw),
            ds.dir.joinpath('TRANSCRIPTION.md'),
            log=args.log)
        res = readme.report(ds, tr, **kw)
        if res:
            textdump(res, ds.dir.joinpath('README.md'), log=args.log)

    with_dataset(args, _run)
