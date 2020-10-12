import collections

from clldutils.misc import nfilter

from pylexibank.util import get_badge


def build_status_badge(dataset):
    if dataset.dir.joinpath('.travis.yml').exists() and dataset.repo and dataset.repo.github_repo:
        return "[![Build Status](https://travis-ci.org/{0}.svg?branch=master)]" \
               "(https://travis-ci.org/{0})".format(dataset.repo.github_repo)
    return ''


def report(dataset, tr_analysis=None, glottolog=None, log=None):
    #
    # FIXME: in case of multiple cldf datasets:
    # - write only summary into README.md
    # - separate lexemes.md and transcriptions.md
    #
    lines = []

    # add NOTES.md
    if dataset.dir.joinpath('NOTES.md').exists():
        lines.append('## Notes\n')
        lines.append(dataset.dir.joinpath('NOTES.md').read_text() + '\n\n')

    badges = nfilter([build_status_badge(dataset)])

    for cldf_spec in dataset.cldf_specs_dict.values():
        lines.extend(cldf_report(cldf_spec, tr_analysis, badges, log, glottolog))
        break
    return '\n'.join(lines)


def cldf_report(cldf_spec, tr_analysis, badges, log, glottolog):
    lines = []
    if not list(cldf_spec.dir.glob('*.csv')):
        return lines

    if cldf_spec.module != 'Wordlist':
        return lines  # pragma: no cover

    cldf = cldf_spec.get_dataset()

    synonyms = collections.defaultdict(collections.Counter)
    totals = {
        'languages': collections.Counter(),
        'concepts': collections.Counter(),
        'sources': collections.Counter(),
        'cognate_sets': collections.Counter(),
        'lexemes': 0,
        'lids': collections.Counter(),
        'cids': collections.Counter(),
        'sids': collections.Counter(),
    }

    missing_source = []
    missing_lang = []

    param2concepticon = {r['ID']: r['Concepticon_ID'] for r in cldf['ParameterTable']}
    lang2glottolog = {r['ID']: r['Glottocode'] for r in cldf['LanguageTable']}

    for row in cldf['FormTable']:
        if row['Source']:
            totals['sources'].update(['y'])
            totals['sids'].update(row['Source'])
        else:
            missing_source.append(row)
        totals['concepts'].update([param2concepticon[row['Parameter_ID']]])
        totals['languages'].update([lang2glottolog[row['Language_ID']]])
        totals['lexemes'] += 1
        totals['lids'].update([row['Language_ID']])
        totals['cids'].update([row['Parameter_ID']])
        synonyms[row['Language_ID']].update([row['Parameter_ID']])

    for row in cldf.get('CognateTable') or []:
        totals['cognate_sets'].update([row['Cognateset_ID']])

    sindex = sum(
        [sum(list(counts.values())) / float(len(counts)) for counts in synonyms.values()])
    langs = set(synonyms.keys())
    if langs:
        sindex /= float(len(langs))
    else:
        sindex = 0  # pragma: no cover
    totals['SI'] = sindex

    if tr_analysis:
        stats = tr_analysis['stats']
    else:
        stats = collections.defaultdict(list)

    lsegments = len(stats['segments'])
    lbipapyerr = len(stats['bipa_errors'])
    lsclasserr = len(stats['sclass_errors'])

    def ratio(prop):
        if float(totals['lexemes']) == 0:
            return 0  # pragma: no cover
        return sum(v for k, v in totals[prop].items() if k) / float(totals['lexemes'])

    num_cognates = sum(1 for k, v in totals['cognate_sets'].items())
    # see List et al. 2017
    # diff between cognate sets and meanings / diff between words and meanings
    try:
        cog_diversity = (num_cognates - len(totals['cids'])) \
            / (totals['lexemes'] - len(totals['cids']))
    except ZeroDivisionError:
        cog_diversity = 0.0  # no lexemes.

    badges = badges[:]
    badges.extend([
        get_badge(ratio('languages'), 'Glottolog'),
        get_badge(ratio('concepts'), 'Concepticon'),
        get_badge(ratio('sources'), 'Source'),
    ])
    if lsegments:
        badges.extend([
            get_badge((lsegments - lbipapyerr) / lsegments, 'BIPA'),
            get_badge((lsegments - lsclasserr) / lsegments, 'CLTS SoundClass'),
        ])
    lines.extend(['## Statistics', '\n', '\n'.join(badges), ''])
    stats_lines = [
        '- **Varieties:** {0:,}'.format(len(totals['lids'])),
        '- **Concepts:** {0:,}'.format(len(totals['cids'])),
        '- **Lexemes:** {0:,}'.format(totals['lexemes']),
        '- **Sources:** {0:,}'.format(len(totals['sids'])),
        '- **Synonymy:** {:0.2f}'.format(totals['SI']),
    ]
    if num_cognates:
        stats_lines.extend([
            '- **Cognacy:** {0:,} cognates in {1:,} cognate sets ({2:,} singletons)'.format(
                sum(v for k, v in totals['cognate_sets'].items()),
                num_cognates, len([k for k, v in totals['cognate_sets'].items() if v == 1])),
            '- **Cognate Diversity:** {:0.2f}'.format(cog_diversity)
        ])
    if stats['segments']:
        stats_lines.extend([
            '- **Invalid lexemes:** {0:,}'.format(stats['invalid_words_count']),
            '- **Tokens:** {0:,}'.format(sum(stats['segments'].values())),
            '- **Segments:** {0:,} ({1} BIPA errors, {2} CTLS sound class errors, '
            '{3} CLTS modified)'
            .format(lsegments, lbipapyerr, lsclasserr, len(stats['replacements'])),
            '- **Inventory size (avg):** {:0.2f}'.format(stats['inventory_size']),
        ])

    if log:
        log.info(
            '\n'.join(['Summary for dataset {}'.format(cldf_spec.metadata_path)] + stats_lines))
    lines.extend(stats_lines)

    totals['languages'] = len(totals['lids'])
    totals['concepts'] = len(totals['cids'])
    totals['cognate_sets'] = bool(1 for k, v in totals['cognate_sets'].items() if v > 1)

    bookkeeping_languoids_in_gl = set()
    if glottolog:
        for lang in glottolog.api.languoids():
            if lang.category == 'Bookkeeping':
                bookkeeping_languoids_in_gl.add(lang.id)  # pragma: no cover

    bookkeeping_languoids = []
    for lang in cldf['LanguageTable']:
        if lang.get('Glottocode') in bookkeeping_languoids_in_gl:
            bookkeeping_languoids.append(lang)  # pragma: no cover

    # improvements section
    if missing_lang or missing_source or bookkeeping_languoids:
        lines.extend(['\n## Possible Improvements:\n', ])

        if missing_lang:  # pragma: no cover
            lines.append("- Languages missing glottocodes: %d/%d (%.2f%%)" % (
                len(missing_lang),
                totals['languages'],
                (len(missing_lang) / totals['languages']) * 100
            ))

        if bookkeeping_languoids:  # pragma: no cover
            lines.append(
                "- Languages linked to [bookkeeping languoids in Glottolog]"
                "(http://glottolog.org/glottolog/glottologinformation"
                "#bookkeepinglanguoids):")
        for lang in bookkeeping_languoids:  # pragma: no cover
            lines.append(
                '  - {0} [{1}](http://glottolog.org/resource/languoid/id/{1})'.format(
                    lang.get('Name', lang.get('ID')), lang['Glottocode']))
        lines.append('\n')

    if missing_source:
        lines.append("- Entries missing sources: %d/%d (%.2f%%)" % (
            len(missing_source),
            totals['lexemes'],
            (len(missing_source) / totals['lexemes']) * 100
        ))

    return lines
