import collections

import attr
import pyclts
import pyclts.models
from clldutils.markup import Table


@attr.s
class Analysis(object):
    # map segments to frequency
    segments = attr.ib(default=attr.Factory(collections.Counter))
    # aggregate segments which are invalid for lingpy
    bipa_errors = attr.ib(default=attr.Factory(set))
    # aggregate segments which are invalid for clpa
    sclass_errors = attr.ib(default=attr.Factory(set))
    # map clpa-replaceable segments to their replacements
    replacements = attr.ib(default=collections.defaultdict(set))
    # count number of errors
    general_errors = attr.ib(default=0)


@attr.s
class Stats(Analysis):
    inventory_size = attr.ib(default=0)
    invalid_words = attr.ib(default=attr.Factory(list))
    invalid_words_count = attr.ib(default=0)
    bad_words = attr.ib(default=attr.Factory(list))
    bad_words_count = attr.ib(default=0)


# Note: We use a mutable default argument intentionally to serve as a cache.
def analyze(clts, segments, analysis, lookup=dict(bipa={}, dolgo={})):
    """
    Test a sequence for compatibility with CLPA and LingPy.

    :param analysis: Pass a `TranscriptionAnalysis` instance for cumulative reporting.
    """
    # raise a ValueError in case of empty segments/strings
    if not segments:
        raise ValueError('Empty sequence.')

    # test if at least one element in `segments` has information
    # (helps to catch really badly formed input, such as ['\n']
    if not [segment for segment in segments if segment.strip()]:
        raise ValueError('No information in the sequence.')

    # build the phonologic and sound class analyses
    try:
        bipa_analysis, sc_analysis = [], []
        for s in segments:
            a = lookup['bipa'].get(s)
            if a is None:
                a = lookup['bipa'].setdefault(s, clts.bipa[s])
            bipa_analysis.append(a)

            sc = lookup['dolgo'].get(s)
            if sc is None:
                sc = lookup['dolgo'].setdefault(s, clts.bipa.translate(s, clts.soundclass('dolgo')))
            sc_analysis.append(sc)
    except:  # noqa; pragma: no cover
        print(segments)
        raise

    # compute general errors; this loop must take place outside the
    # following one because the code for computing single errors (either
    # in `bipa_analysis` or in `soundclass_analysis`) is unnecessary
    # complicated
    for sound_bipa, sound_class in zip(bipa_analysis, sc_analysis):
        if isinstance(sound_bipa, pyclts.models.UnknownSound) or sound_class == '?':
            analysis.general_errors += 1

    # iterate over the segments and analyses, updating counts of occurrences
    # and specific errors
    for segment, sound_bipa, sound_class in zip(segments, bipa_analysis, sc_analysis):
        # update the segment count
        analysis.segments.update([segment])

        # add an error if we got an unknown sound, otherwise just append
        # the `replacements` dictionary
        if isinstance(sound_bipa, pyclts.models.UnknownSound):
            analysis.bipa_errors.add(segment)
        else:
            analysis.replacements[sound_bipa.source].add(str(sound_bipa))

        # update sound class errors, if any
        if sound_class == '?':
            analysis.sclass_errors.add(segment)

    return segments, bipa_analysis, sc_analysis, analysis


TEMPLATE = """
# Detailed transcription record

## Segments

{0}

## Unsegmentable lexemes (up to 100 only)

{1}

## Words with invalid segments (up to 100 only)

{2}
"""


def report(analysis):
    segments = Table('Segment', 'Occurrence', 'BIPA', 'CLTS SoundClass')
    for a, b in sorted(
            analysis['stats']['segments'].items(), key=lambda x: (-x[1], x[0])):
        c, d = '✓', '✓'
        if a in analysis['stats']['sclass_errors']:
            c = '✓' if a not in analysis['stats']['bipa_errors'] else '?'
            d = ', '.join(analysis['stats']['sclass_errors'][a]) \
                if a not in analysis['stats']['sclass_errors'] else '?'

        # escape pipe for markdown table if necessary
        a = a.replace('|', '&#124;')

        segments.append([a, b, c, d])

    invalid = Table('ID', 'LANGUAGE', 'CONCEPT', 'FORM')
    for row in analysis['stats']['invalid_words']:
        invalid.append(row)  # pragma: no cover

    words = Table('ID', 'LANGUAGE', 'CONCEPT', 'FORM', 'SEGMENTS')
    for row in analysis['stats']['bad_words']:
        words.append(row)
    return TEMPLATE.format(
        segments.render(verbose=True),
        invalid.render(verbose=True),
        words.render(verbose=True))
