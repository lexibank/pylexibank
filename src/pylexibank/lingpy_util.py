# coding=utf-8
from __future__ import unicode_literals, print_function
from copy import deepcopy

import lingpy
from clldutils.misc import slug

from pylexibank.dataset import Cognate


def wordlist2cognates(wordlist, source, expert='expert', ref='cogid'):
    """Turn a wordlist into a cognate set list, using the cldf parameters."""
    for k in wordlist:
        yield dict(
            Form_ID=wordlist[k, 'lid'],
            ID=k,
            Form=wordlist[k, 'ipa'],
            Cognateset_ID='{0}-{1}'.format(
                slug(wordlist[k, 'concept']), wordlist[k, ref]),
            Cognate_Detection_Method=expert,
            Source=source)


def _cldf2wld(dataset):
    """Make lingpy-compatible dictinary out of cldf main data."""
    header = [f for f in dataset.dataset.lexeme_class.fieldnames() if f != 'ID']
    D = {0: ['lid'] + [h.lower() for h in header]}
    for idx, row in enumerate(dataset.objects['FormTable']):
        row = deepcopy(row)
        row['Segments'] = ' '.join(row['Segments'])
        D[idx + 1] = [row['ID']] + [row[h] for h in header]
    return D


def _cldf2lexstat(
        dataset,
        segments='segments',
        transcription='value',
        row='parameter_id',
        col='language_id'):
    """Read LexStat object from cldf dataset."""
    D = _cldf2wld(dataset)
    return lingpy.LexStat(D, segments=segments, transcription=transcription, row=row, col=col)


def _cldf2wordlist(dataset, row='parameter_id', col='language_id'):
    """Read worldist object from cldf dataset."""
    return lingpy.Wordlist(_cldf2wld(dataset), row=row, col=col)


def iter_cognates(dataset, column='Segments', method='turchin', threshold=0.5, **kw):
    """
    Compute cognates automatically for a given dataset.
    """
    if method == 'turchin':
        for row in dataset.objects['FormTable']:
            sounds = ''.join(lingpy.tokens2class(row[column], 'dolgo'))
            if sounds.startswith('V'):
                sounds = 'H' + sounds
            sounds = '-'.join([s for s in sounds if s != 'V'][:2])
            cogid = slug(row['Parameter_ID']) + '-' + sounds
            if '0' not in sounds:
                yield dict(
                    Form_ID=row['ID'],
                    Form=row['Value'],
                    Cognateset_ID=cogid,
                    Cognate_Detection_Method='CMM')

    if method in ['sca', 'lexstat']:
        lex = _cldf2lexstat(dataset)
        if method == 'lexstat':
            lex.get_scorer(**kw)
        lex.cluster(method=method, threshold=threshold, ref='cogid')
        for k in lex:
            yield Cognate(
                Form_ID=lex[k, 'lid'],
                Form=lex[k, 'value'],
                Cognateset_ID=lex[k, 'cogid'],
                Cognate_Detection_Method=method + '-t{0:.2f}'.format(threshold))


def iter_alignments(dataset, cognate_sets, column='Segments', method='library'):
    """
    Function computes automatic alignments and writes them to file.
    """
    if not isinstance(dataset, lingpy.basic.parser.QLCParser):
        wordlist = _cldf2wordlist(dataset)
        cognates = {r['Form_ID']: r for r in cognate_sets}
        wordlist.add_entries(
            'cogid',
            'lid',
            lambda x: cognates[x]['Cognateset_ID'] if x in cognates else '')
        for i, k in enumerate(wordlist):
            if not wordlist[k, 'cogid']:
                wordlist[k][wordlist.header['cogid']] = 'empty-%s' % i
        alm = lingpy.Alignments(
            wordlist,
            ref='cogid',
            row='parameter_id',
            col='language_id',
            segments=column.lower())
        alm.align(method=method)
        for k in alm:
            if alm[k, 'lid'] in cognates:
                cognate = cognates[alm[k, 'lid']]
                cognate['Alignment'] = alm[k, 'alignment'].split(' ')
                cognate['Alignment_Method'] = method
    else:
        alm = lingpy.Alignments(dataset, ref='cogid')
        alm.align(method=method)

        for cognate in cognate_sets:
            idx = cognate['ID'] or cognate['Form_ID']
            cognate['Alignment'] = alm[int(idx), 'alignment'].split(' ')
            cognate['Alignment_Method'] = 'SCA-' + method


def lingpy_subset(path, header, errors=2):
    try:
        wl = lingpy.get_wordlist(path, col='language_name', row='parameter_name')
    except ValueError:
        return []
    data = []

    if 'segments' not in wl.header:
        return []
    for taxon in wl.cols:
        error_count = 0
        idxs = wl.get_list(col=taxon, flat=True)
        goodlist = []
        for idx, segments in [(idx, wl[idx, 'segments']) for idx in idxs]:
            if wl[idx, 'language_id'] and wl[idx, 'parameter_id']:
                cv = lingpy.tokens2class(segments.split(), 'cv')
                if '0' in cv:
                    error_count += 1
                else:
                    l_ = sum(1 for x in cv if x != 'T')
                    if l_:
                        goodlist += [(idx, l_)]
                if error_count > errors:
                    goodlist = []
                    break
        for idx, l in goodlist:
            data.append([wl[idx, h] for h in header] + ['{0}'.format(l)])
    return data
