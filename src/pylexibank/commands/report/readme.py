# *-* coding: utf-8 *-*
"""
Implements the readme file generator.
"""
from __future__ import division, unicode_literals, print_function
from collections import Counter, defaultdict

from pylexibank.util import get_badge, get_variety_id, jsondump


def build_status_badge(ds):
    if not ds.dir.joinpath('.travis.yml').exists():
        return ''
    try:
        return "[![Build Status](https://travis-ci.org/{0}.svg?branch=master)]" \
               "(https://travis-ci.org/{0})".format(ds.github_repo)
    except:
        return ''


def report(ds, tr_analysis, log=None, **kw):
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
        lid = get_variety_id(row)
        totals['languages'].update([lid])
        totals['lexemes'] += 1
        if lid and row['Parameter_ID']:
            synonyms[lid].update([row['Parameter_ID']])

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
    llingpyerr = len(stats['lingpy_errors'])
    lclpaerr = len(stats['clpa_errors'])

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
            get_badge((lsegments - llingpyerr) / lsegments, 'LingPy'),
            get_badge((lsegments - lclpaerr) / lsegments, 'CLPA'),
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
        '- **Segments:** {0:,} ({1} LingPy errors, {2} CLPA errors, {3} CLPA modified)'
        .format(lsegments, llingpyerr, lclpaerr, len(stats['replacements'])),
        '- **Inventory size (avg):** %.2f' % stats['inventory_size'],
    ]
    if log:
        log.info('\n'.join(['Summary for dataset {}'.format(ds.id)] + stats_lines))
    lines.extend(stats_lines)

    # improvements section
    if len(missing_lang) or len(missing_source) or len(missing_concept):
        lines.extend(['\n## Possible Improvements:\n', ])
        
        if len(missing_lang):
            lines.append("- Languages missing glottocodes: %d/%d (%.2f%%)" % (
                len(missing_lang),
                len(totals['languages']),
                (len(missing_lang) / len(totals['languages'])) * 100
            ))
            
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

    jsondump(totals, ds.dir.joinpath('README.json'))
    return lines + trlines
