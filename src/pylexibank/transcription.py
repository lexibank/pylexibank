"""
Functionality to analyze transcriptions.
"""
import itertools
import collections
from collections.abc import Iterable
import dataclasses
from typing import Any, Union

import pyclts
import pyclts.models
from clldutils.markup import Table


@dataclasses.dataclass
class Analysis:
    """Results of a transcription analysis."""
    #
    # This is written per language to .transcription-report.json
    #
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

    def to_json(self):
        """Return an object suitable for serialization as JSON."""
        return collections.OrderedDict([
            ('bipa_errors', sorted(self.bipa_errors)),
            ('general_errors', self.general_errors),
            ('replacements', collections.OrderedDict(
                (k, sorted(v)) for k, v in sorted(self.replacements.items()))),
            ('sclass_errors', sorted(self.sclass_errors)),
            ('segments', collections.OrderedDict(sorted(self.segments.items()))),
        ])

    @property
    def error_segments(self) -> set[str]:
        """Set of invalid segments encountered so far."""
        return self.bipa_errors.union(self.sclass_errors)


@dataclasses.dataclass
class Stats(Analysis):
    """Summary stats about a transcription analysis."""
    #
    # This is written as aggregated stats to .transcription-report.json
    #
    inventory_size: int = 0
    invalid_words: list = dataclasses.field(default_factory=list)
    # We need to store the count, too, because when initialized from a JSON report, at most 100
    # words will be loaded, but there may have been more.
    invalid_words_count: int = 0
    bad_words: list = dataclasses.field(default_factory=list)
    bad_words_count: int = 0

    def to_json(self):
        """Return an object suitable for serialization as JSON."""
        res = super().to_json()
        res.update(collections.OrderedDict([
            ('bad_words', sorted(self.bad_words[:100])),
            ('bad_words_count', self.bad_words_count),
            ('invalid_words', sorted(self.invalid_words[:100])),
            ('invalid_words_count', self.invalid_words_count),
            ('inventory_size', self.inventory_size),
        ]))
        return res


@dataclasses.dataclass
class Report:
    """A transcription report."""
    by_language: dict[str, Analysis] = dataclasses.field(default_factory=dict)
    stats: Stats = dataclasses.field(default_factory=Stats)
    TEMPLATE = """
# Detailed transcription record

## Segments

{0}

## Unsegmentable lexemes (up to 100 only)

{1}

## Words with invalid segments (up to 100 only)

{2}
"""

    def add_bad_word(self, row: dict):
        """Add a form with non-BIPA segments to the report."""
        # Note: At this point, the error segments have been added to the language-specific analysis.
        error_segments = self.by_language[row['Language_ID']].error_segments
        self.stats.bad_words.append([
            row['ID'],
            row['Language_ID'],
            row['Parameter_ID'],
            row['Form'],
            ' '.join(f'<s> {s} </s>' if s in error_segments else s for s in row["Segments"])])
        self.stats.bad_words_count += 1

    def add_invalid_word(self, row: dict[str, Any]):
        """Add an invalid form to the report."""
        self.stats.invalid_words.append([
            row['ID'],
            row['Language_ID'],
            row['Parameter_ID'],
            row['Form'],
        ])
        self.stats.invalid_words_count += 1

    def compute_stats(self):
        """Aggregate the language-specific information, updating relevant summary stats."""
        for analysis in self.by_language.values():
            for attribute in ['segments', 'bipa_errors', 'sclass_errors', 'replacements']:
                getattr(self.stats, attribute).update(getattr(analysis, attribute))
            self.stats.general_errors += analysis.general_errors
            self.stats.inventory_size += len(analysis.segments) / len(self.by_language)

    def to_json(self) -> collections.OrderedDict:
        """Return an object suitable for serialization as JSON."""
        return collections.OrderedDict([
            ('by_language', collections.OrderedDict(
                [(k, v.to_json()) for k, v in sorted(self.by_language.items())])),
            ('stats', self.stats.to_json()),
        ])

    def get_analysis(self, lid: str) -> Analysis:
        """Return the Analysis object for a given language."""
        if lid not in self.by_language:
            self.by_language[lid] = Analysis()
        return self.by_language[lid]

    def __str__(self) -> str:
        """Format the transcription report as Markdown suitable for inclusion in the README."""
        segments = Table('Segment', 'Occurrence', 'BIPA', 'CLTS SoundClass')
        for a, b in sorted(self.stats.segments.items(), key=lambda x: (-x[1], x[0])):
            c = '✓' if a not in self.stats.bipa_errors else '?'
            d = '✓' if a not in self.stats.sclass_errors else '?'
            # escape pipe for markdown table if necessary
            a = a.replace('|', '&#124;')
            segments.append([a, b, c, d])

        invalid = Table('ID', 'LANGUAGE', 'CONCEPT', 'FORM')
        for row in self.stats.invalid_words[:100]:
            invalid.append(row)  # pragma: no cover

        words = Table('ID', 'LANGUAGE', 'CONCEPT', 'FORM', 'SEGMENTS')
        for row in self.stats.bad_words[:100]:
            words.append(row)
        return self.TEMPLATE.format(
            segments.render(verbose=True),
            invalid.render(verbose=True),
            words.render(verbose=True))


def valid_sequence(segments: list[str]) -> Union[bool, list[str]]:
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


def analyze_segments(clts: pyclts.CLTS, form_data: dict, report: Report, with_morphemes: bool):
    """Analyze the segments of a form."""
    analysis = report.get_analysis(form_data['Language_ID'])
    try:
        segments = form_data['Segments']
        if with_morphemes:
            segments = list(itertools.chain(*[s.split() for s in segments]))
        valid = valid_sequence(segments)
        _, _bipa, _sc, _analysis = analyze(clts, segments, analysis)

        # update the list of `bad_words` if necessary; we precompute a
        # list of data types in `_bipa` just to make the conditional
        # checking easier
        _bipa_types = [type(s) for s in _bipa]
        if (pyclts.models.UnknownSound in _bipa_types) or '?' in _sc or not valid:
            report.add_bad_word(form_data)
    except ValueError:  # pragma: no cover
        report.add_invalid_word(form_data)
    except (KeyError, AttributeError):  # pragma: no cover
        print(form_data['Form'], form_data)
        raise
