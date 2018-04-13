# coding: utf8
from __future__ import unicode_literals, print_function, division

from clldutils import jsonlib

from pylexibank.util import textdump
from pylexibank.commands.report import readme
from pylexibank.commands.report import transcription


def report(ds, **kw):
    """Create a README.md file listing the contents of a dataset

    lexibank report [DATASET_ID]
    """
    tr = jsonlib.load(ds.dir.joinpath('transcription.json'))
    textdump(
        transcription.report(tr, **kw),
        ds.dir.joinpath('TRANSCRIPTION.md'),
        log=kw.get('log'))
    res = readme.report(ds, tr, **kw)
    if res:
        textdump(res, ds.dir.joinpath('README.md'), log=kw.get('log'))
