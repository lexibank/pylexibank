# coding: utf8
from __future__ import unicode_literals, print_function, division
from collections import Counter, defaultdict

from clldutils.markup import Table

from pylexibank.util import textdump, get_badge


def report(ds, **kw):
    """Create a README.md file listing the contents of a dataset

    lexibank report [DATASET_ID]
    """
    tr = ds.read_json().get('transcription', {})
    textdump(
        _transcription(tr, **kw),
        ds.dir.joinpath('TRANSCRIPTION.md'),
        log=kw.get('log'))
    res = _readme(ds, tr, **kw)
    if res:
        textdump(res, ds.dir.joinpath('README.md'), log=kw.get('log'))


def build_status_badge(ds):
    if not ds.dir.joinpath('.travis.yml').exists():
        return ''
    try:
        return "[![Build Status](https://travis-ci.org/{0}.svg?branch=master)]" \
               "(https://travis-ci.org/{0})".format(ds.github_repo)
    except:
        return ''


def _readme(ds, tr_analysis, log=None, **kw):
    #
    # FIXME: write only summary into README.md
    # in case of multiple cldf datasets:
    # - separate lexemes.md and transcriptions.md
    #
    if not list(ds.cldf_dir.glob('*.csv')):
        return
    lines = [
        '# %s' % ds.metadata.title,
        '',
        'Cite the source dataset as',
        '',
        '> %s' % ds.metadata.citation,
        '']

    if ds.metadata.license:
        lines.extend([
            'This dataset is licensed under a %s license' % ds.metadata.license, ''])

    if ds.metadata.url:
        lines.extend(['Available online at %s' % ds.metadata.url, ''])

    if ds.metadata.related:
        lines.extend(['See also %s' % ds.metadata.related, ''])

    if ds.metadata.conceptlist:
        lines.extend([
            'Conceptlist in Concepticon: [{0}](http://concepticon.clld.org/contributions'
            '/{0})'.format(ds.metadata.conceptlist),
            ''])

    # add NOTES.md
    if ds.dir.joinpath('NOTES.md').exists():
        lines.extend(['## Notes', ''])
        lines.extend(ds.dir.joinpath('NOTES.md').read_text().split("\n"))
        lines.extend(['', ''])  # some blank lines

    trlines = []

    synonyms = defaultdict(Counter)
    totals = {
        'languages': Counter(),
        'concepts': Counter(),
        'sources': Counter(),
        'cognate_sets': Counter(),
        'lexemes': 0,
    }

    missing_source = []
    missing_lang = [L['NAME'] for L in ds.languages if not L['GLOTTOCODE']]
    missing_param = []
    missing_concept = [c for c in ds.concepts if not c['CONCEPTICON_ID']]

    for row in ds.cldf['FormTable']:
        if row['Source']:
            totals['sources'].update(['y'])
        else:
            missing_source.append(row)
        if row['Parameter_ID']:
            totals['concepts'].update([row['Parameter_ID']])
        else:
            missing_param.append(row)
        totals['languages'].update([row['Language_ID']])
        totals['lexemes'] += 1
        if row['Language_ID'] and row['Parameter_ID']:
            synonyms[row['Language_ID']].update([row['Parameter_ID']])

    for row in ds.cldf['CognateTable']:
        totals['cognate_sets'].update([row['Cognateset_ID']])

    sindex = sum(
        [sum(list(counts.values())) / float(len(counts)) for counts in synonyms.values()])
    langs = set(synonyms.keys())
    if langs:
        sindex /= float(len(langs))
    else:
        sindex = 0
    totals['SI'] = sindex

    stats = tr_analysis['stats']
    lsegments = len(stats['segments'])
    lbipapyerr = len(stats['bipa_errors'])
    lsclasserr = len(stats['sclass_errors'])

    def ratio(prop):
        return sum(v for k, v in totals[prop].items() if k) / float(totals['lexemes'])

    badges = [
        build_status_badge(ds),
        get_badge(ratio('languages'), 'Glottolog'),
        get_badge(ratio('concepts'), 'Concepticon'),
        get_badge(ratio('sources'), 'Source'),
    ]
    if lsegments:
        badges.extend([
            get_badge((lsegments - lbipapyerr) / lsegments, 'BIPA'),
            get_badge((lsegments - lsclasserr) / lsegments, 'CLTS SoundClass'),
        ])
    lines.extend(['## Statistics', '\n', '\n'.join(badges), ''])
    stats_lines = [
        '- **Varieties:** {0:,}'.format(len(totals['languages'])),
        '- **Concepts:** {0:,}'.format(len(totals['concepts'])),
        '- **Lexemes:** {0:,}'.format(totals['lexemes']),
        '- **Synonymy:** %.2f' % (totals['SI']),
        '- **Cognacy:** {0:,} cognates in {1:,} cognate sets'.format(
            sum(v for k, v in totals['cognate_sets'].items() if v > 1),
            sum(1 for k, v in totals['cognate_sets'].items() if v > 1)),
        '- **Invalid lexemes:** {0:,}'.format(stats['invalid_words_count']),
        '- **Tokens:** {0:,}'.format(sum(stats['segments'].values())),
        '- **Segments:** {0:,} ({1} BIPA errors, {2} CTLS sound class errors, {3} CLTS modified)'
            .format(lsegments, lbipapyerr, lsclasserr, len(stats['replacements'])),
        '- **Inventory size (avg):** %.2f' % stats['inventory_size'],
        ]
    if log:
        log.info('\n'.join(['Summary for dataset {}'.format(ds.id)] + stats_lines))
    lines.extend(stats_lines)

    totals['languages'] = len(totals['languages'])
    totals['concepts'] = len(totals['concepts'])
    totals['cognate_sets'] = bool(1 for k, v in totals['cognate_sets'].items() if v > 1)
    totals['sources'] = totals['sources'].get('y', 0)

    bookkeeping_languoids = []
    for lang in ds.cldf['LanguageTable']:
        gl_lang = ds.glottolog.cached_languoids.get(lang.get('Glottocode'))
        if gl_lang and gl_lang.category == 'Bookkeeping':
            bookkeeping_languoids.append(lang)

    # improvements section
    if len(missing_lang) or len(missing_source) or len(missing_concept) or bookkeeping_languoids:
        lines.extend(['\n## Possible Improvements:\n', ])

        if len(missing_lang):
            lines.append("- Languages missing glottocodes: %d/%d (%.2f%%)" % (
                len(missing_lang),
                totals['languages'],
                (len(missing_lang) / totals['languages']) * 100
            ))

        if bookkeeping_languoids:
            lines.append(
                "- Languages linked to [bookkeeping languoids in Glottolog]"
                "(http://glottolog.org/glottolog/glottologinformation"
                "#bookkeepinglanguoids):")
            for lang in bookkeeping_languoids:
                lines.append(
                    '  - {0} [{1}](http://glottolog.org/resource/languoid/id/{1})'.format(
                        lang.get('Name', lang.get('ID')), lang['Glottocode']))
            lines.append('\n')

        if len(missing_source):
            lines.append("- Entries missing sources: %d/%d (%.2f%%)" % (
                len(missing_source),
                totals['lexemes'],
                (len(missing_source) / totals['lexemes']) * 100
            ))

        if len(missing_concept):
            lines.append("- Entries missing concepts: %d/%d (%.2f%%)" % (
                len(missing_param),
                totals['lexemes'],
                (len(missing_param) / totals['lexemes']) * 100
            ))
        lines.append("\n")

    return lines + trlines


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
* Number of BIPA-Errors: {bipa_errors}
* Number of CLTS-SoundClass-Errors: {sclass_errors}
* Bad words: {words_errors}
"""


def _transcription(analysis, **kw):
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
        invalid.append(row)

    words = Table('ID', 'LANGUAGE', 'CONCEPT', 'FORM', 'SEGMENTS')
    for row in analysis['stats']['bad_words']:
        words.append(row)
    return TEMPLATE.format(
        segments.render(verbose=True),
        invalid.render(verbose=True),
        words.render(verbose=True))
