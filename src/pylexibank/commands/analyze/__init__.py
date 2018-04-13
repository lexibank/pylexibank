# coding: utf8
from __future__ import unicode_literals, print_function, division

from pylexibank.util import jsondump
from pylexibank.commands.analyze import transcription


def analyze(ds, **kw):
    """
    Analyzes a dataset.

    lexibank analyze DATASET_ID
    """
    jsondump(
        transcription.analyze(ds),
        ds.dir.joinpath('transcription.json'),
        log=kw.get('log'))
