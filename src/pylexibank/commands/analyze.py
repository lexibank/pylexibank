# coding: utf8
from __future__ import unicode_literals, print_function, division

import attr
from lingpy import rc

from pylexibank.lingpy_util import test_sequences, TranscriptionAnalysis
from pylexibank.util import pb


def analyze(ds, **kw):
    """
    Analyzes a dataset.

    lexibank analyze DATASET_ID
    """
    ds.write_json(dict(transcription=_analyze(ds)))


@attr.s
class TranscriptionStats(TranscriptionAnalysis):
    inventory_size = attr.ib(default=0)
    invalid_words = attr.ib(default=attr.Factory(list))
    invalid_words_count = attr.ib(default=0)
    bad_words = attr.ib(default=attr.Factory(list))
    bad_words_count = attr.ib(default=0)


def _analyze(dataset):
    rc(schema=dataset.metadata.lingpy_schema or 'ipa')
    ans, bad_words, invalid_words = test_sequences(dataset.cldf, model='dolgo')

    stats = TranscriptionStats(
        bad_words=sorted(bad_words[:100], key=lambda x: x['ID']),
        bad_words_count=len(bad_words),
        invalid_words=sorted(invalid_words[:100], key=lambda x: x['ID']),
        invalid_words_count=len(invalid_words))
    for lid, analysis in ans.items():
        for attribute in ['segments', 'bipa_errors', 'sclass_errors', 'replacements']:
            getattr(stats, attribute).update(getattr(analysis, attribute))
        stats.general_errors += analysis.general_errors
        stats.inventory_size += len(analysis.segments) / len(ans)

    error_segments = stats.bipa_errors.union(stats.sclass_errors)
    for i, row in pb(enumerate(stats.bad_words)):
        analyzed_segments = []
        for s in row['Segments']:
            analyzed_segments.append('<s> %s </s>' % s if s in error_segments else s)
        stats.bad_words[i] = [
            row['ID'],
            row['Language_ID'],
            row['Parameter_ID'],
            row['Form'],
            ' '.join(analyzed_segments)]

    for i, row in enumerate(stats.invalid_words):
        stats.invalid_words[i] = [
            row['ID'],
            row['Language_ID'],
            row['Parameter_ID'],
            row['Form']]

    return dict(
        by_language={k: attr.asdict(v) for k, v in ans.items()}, stats=attr.asdict(stats))
