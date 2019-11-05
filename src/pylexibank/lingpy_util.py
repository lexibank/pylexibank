import lingpy
from clldutils.misc import slug
import pycldf


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
    """Make lingpy-compatible dictionary out of cldf main data."""
    forms = dataset.objects['FormTable'] \
        if hasattr(dataset, 'objects') else list(dataset['FormTable'])
    if not forms:
        raise ValueError('No forms')

    idcol = dataset['FormTable', 'id'].name if isinstance(dataset, pycldf.Dataset) else 'ID'
    header = [f for f in forms[0].keys() if f != idcol]
    D = {0: ['lid'] + [h.lower() for h in header]}
    for idx, row in enumerate(forms):
        D[idx + 1] = [row[idcol]] + [row[h] for h in header]
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

    :param dataset: Either a `LexibankWriter` instance or a `pycldf.Dataset`.
    """
    forms = dataset.objects['FormTable'] \
        if hasattr(dataset, 'objects') else list(dataset['FormTable'])

    if method == 'turchin':
        for row in forms:
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
        try:
            lex = _cldf2lexstat(dataset)
        except ValueError:
            return
        if method == 'lexstat':
            lex.get_scorer(**kw)
        lex.cluster(method=method, threshold=threshold, ref='cogid')
        for k in lex:
            yield dict(
                Form_ID=lex[k, 'lid'],
                Form=lex[k, 'value'],
                Cognateset_ID=lex[k, 'cogid'],
                Cognate_Detection_Method=method + '-t{0:.2f}'.format(threshold))


def iter_alignments(dataset, cognate_sets, column='Segments', method='library', almkw=None):
    """
    Function computes automatic alignments and writes them to file.
    """
    if not isinstance(dataset, lingpy.basic.parser.QLCParser):
        try:
            wordlist = _cldf2wordlist(dataset)
        except ValueError:
            return
        cognates = {r['Form_ID']: r for r in cognate_sets}
        wordlist.add_entries(
            'cogid',
            'lid',
            lambda x: cognates[x]['Cognateset_ID'] if x in cognates else 0)
        alm = lingpy.Alignments(
            wordlist,
            ref='cogid',
            row='parameter_id',
            col='language_id',
            transcription='form',
            segments=column.lower())
        alm.align(method=method)
        for k in alm:
            if alm[k, 'lid'] in cognates:
                cognate = cognates[alm[k, 'lid']]
                cognate['Alignment'] = alm[k, 'alignment']
                cognate['Alignment_Method'] = method
    else:
        almkw = almkw or {}
        almkw.setdefault('ref', 'cogid')
        alm = lingpy.Alignments(dataset, **almkw)
        alm.align(method=method)

        for cognate in cognate_sets:
            idx = cognate.get('ID') or cognate['Form_ID']
            cognate['Alignment'] = alm[int(idx), 'alignment']
            cognate['Alignment_Method'] = 'SCA-' + method
