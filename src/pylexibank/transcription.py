"""
Functionality to analyze transcriptions.
"""
import collections
from collections.abc import Iterable
import dataclasses
from typing import Any

import pyclts
import pyclts.models
from clldutils.markup import Table


@dataclasses.dataclass
class Analysis:
    """Results of a transcription analysis."""
    # map segments to frequency
    segments: dict = dataclasses.field(default_factory=collections.Counter)
    # aggregate segments which are invalid for lingpy
    bipa_errors: set = dataclasses.field(default_factory=set)
    # aggregate segments which are invalid for clpa
    sclass_errors: set = dataclasses.field(default_factory=set)
    # map clpa-replaceable segments to their replacements
    replacements: dict[str, set] = dataclasses.field(default_factory=dict)
    # count number of errors
    general_errors: int = 0


@dataclasses.dataclass
class Stats(Analysis):
    """Summary stats about a transcription analysis."""
    inventory_size: int = 0
    invalid_words: list = dataclasses.field(default_factory=list)
    invalid_words_count: int = 0
    bad_words: list = dataclasses.field(default_factory=list)
    bad_words_count: int = 0


def valid_sequence(segments):
    """
    Make sure that a list of segments does not have any wrong segmentations.
    """
    if not ''.join(segments).strip():
        return False
    if any((
        '_' in segments,
        '#' in segments,
        segments[0] == "+",
        segments[-1] == "+",
        "+" in segments and segments[segments.index("+") + 1] == "+"
    )):
        return False
    return segments


@dataclasses.dataclass
class CachedSegments:
    """We cache lookups in CLTS, since these may be expensive."""
    bipa: dict[str, Any] = dataclasses.field(default_factory=dict)
    dolgo: dict[str, Any] = dataclasses.field(default_factory=dict)

    def get_bipa(self, grapheme: str, clts: pyclts.CLTS):
        """Lookup a BIPA sound."""
        return self.bipa.get(grapheme) or self.bipa.setdefault(grapheme, clts.bipa[grapheme])

    def get_dolgo(self, grapheme: str, clts: pyclts.CLTS):
        """Lookup a Dolgopolsky soundclass."""
        return self.dolgo.get(grapheme) or self.dolgo.setdefault(
            grapheme, clts.bipa.translate(grapheme, clts.soundclass('dolgo')))


# A global segments cache:
SEGMENTS_CACHE = CachedSegments()


# Note: We use a mutable default argument intentionally to serve as a cache.
def analyze(clts: pyclts.CLTS, segments: Iterable[str], analysis: Analysis):
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
    bipa_analysis, sc_analysis = [], []

    for s in segments:
        bipa_analysis.append(SEGMENTS_CACHE.get_bipa(s, clts))
        sc_analysis.append(SEGMENTS_CACHE.get_dolgo(s, clts))

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
            if sound_bipa.source not in analysis.replacements:
                analysis.replacements[sound_bipa.source] = set()
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


def report(analysis: dict) -> str:
    """Format the transcription report as Markdown suitable for inclusion in the README."""
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
