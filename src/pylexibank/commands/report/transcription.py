# coding: utf8
from __future__ import unicode_literals, print_function, division

from clldutils.markup import Table

from pylexibank.util import get_variety_id

TEMPLATE = """
# Detailed transcription record

## Segments

{0}

## Unsegmentable lexemes (up to 100 only)

{1}

## Words with invalid segments (up to 100 only)

{2}
"""

MARKDOWN_TEMPLATE = """
## Transcription Report

### General Statistics

* Number of Tokens: {tokens}
* Number of Segments: {segments}
* Invalid forms: {invalid}
* Inventory Size: {inventory_size:.2f}
* [Erroneous tokens](report.md#tokens): {general_errors}
* Erroneous words: {word_errors}
* Number of LingPy-Errors: {lingpy_errors}
* Number of CLPA-Errors: {clpa_errors}
* Bad words: {words_errors}
"""


def report(analysis, **kw):
    segments = Table('Segment', 'Occurrence', 'LingPy', 'CLPA')
    for a, b in sorted(
            analysis['stats']['segments'].items(), key=lambda x: (-x[1], x[0])):
        c, d = '✓', '✓'
        if a in analysis['stats']['clpa_errors']:
            c = '✓' if a not in analysis['stats']['lingpy_errors'] else '?'
            d = ', '.join(analysis['stats']['clpa_errors'][a]) \
                if a not in analysis['stats']['clpa_errors'] else '?'

        # escape pipe for markdown table if necessary
        a = a.replace('|', '&#124;')

        segments.append([a, b, c, d])

    invalid = Table('ID', 'LANGUAGE', 'CONCEPT', 'FORM')
    for row in analysis['stats']['invalid_words']:
        invalid.append(row)

    words = Table('ID', 'LANGUAGE', 'CONCEPT', 'FORM', 'SEGMENTS')
    for row in analysis['stats']['bad_words']:
        words.append(row)
    return TEMPLATE.format(
        segments.render(verbose=True),
        invalid.render(verbose=True),
        words.render(verbose=True))
