"""
LingPy functionality relevant for Lexibank.
"""
import collections
from collections.abc import Iterable, Generator
from typing import Union, Optional, Any, Literal

import lingpy
from clldutils.misc import slug
import pycldf


def settings() -> collections.OrderedDict[str, Any]:
    """LingPy settings relevant for Lexibank."""
    return collections.OrderedDict([
        (k, str(v) if isinstance(v, lingpy.Model) else v)
        for k, v in sorted(lingpy.settings.rcParams.items(), key=lambda i: i[0])])


def wordlist2cognates(
        wordlist: lingpy.Wordlist,
        source,
        expert: str = 'expert',
        ref: str = 'cogid',
) -> Generator[dict[str, Any], None, None]:
    """Turn a wordlist into a cognate set list, using the cldf parameters."""
    for k in wordlist:
        yield dict(  # pylint: disable=R1735
            Form_ID=wordlist[k, 'lid'],
            ID=k,
            Form=wordlist[k, 'ipa'],
            Cognateset_ID=f"{slug(wordlist[k, 'concept'])}-{wordlist[k, ref]}",
            Cognate_Detection_Method=expert,
            Source=source)


def _get_forms(dataset):
    """
    Return the list of Form `dict`'s for a `cldfbench.CLDFWriter` or a `pycldf.Dataset`.
    """
    return dataset.objects['FormTable'] \
        if (hasattr(dataset, 'objects') and isinstance(dataset.objects, dict)) \
        else list(dataset['FormTable'])


def _cldf2wld(dataset) -> dict[int, list[Any]]:
    """Make lingpy-compatible dictionary out of cldf main data."""
    forms = _get_forms(dataset)
    if not forms:
        raise ValueError('No forms')

    idcol = dataset['FormTable', 'id'].name if isinstance(dataset, pycldf.Dataset) else 'ID'
    header = [f for f in forms[0].keys() if f != idcol]
    d = {0: ['lid'] + [h.lower() for h in header]}
    for idx, row in enumerate(forms):
        d[idx + 1] = [row[idcol]] + [row[h] for h in header]
    return d


def _cldf2lexstat(
        dataset,
        segments='segments',
        transcription='value',
        row='parameter_id',
        col='language_id') -> lingpy.LexStat:
    """Read LexStat object from cldf dataset."""
    return lingpy.LexStat(
        _cldf2wld(dataset), segments=segments, transcription=transcription, row=row, col=col)


def _cldf2wordlist(
        dataset,
        row: str = 'parameter_id',
        col: str = 'language_id',
) -> lingpy.Wordlist:
    """Read worldist object from cldf dataset."""
    return lingpy.Wordlist(_cldf2wld(dataset), row=row, col=col)


def iter_cognates(
        dataset,
        column: str = 'Segments',
        method: Literal['turchin', 'sca', 'lexstat'] = 'turchin',
        threshold: float = 0.5,
        **kw
) -> Generator[dict[str, Any], None, None]:
    """
    Compute cognates automatically for a given dataset.

    :param dataset: Either a `LexibankWriter` instance or a `pycldf.Dataset`.
    """
    forms = _get_forms(dataset)

    if method == 'turchin':
        for row in forms:
            sounds = ''.join(lingpy.tokens2class(row[column], 'dolgo'))
            if sounds.startswith('V'):
                sounds = 'H' + sounds
            sounds = '-'.join([s for s in sounds if s != 'V'][:2])
            cogid = slug(row['Parameter_ID']) + '-' + sounds
            if '0' not in sounds:
                yield dict(  # pylint: disable=R1735
                    Form_ID=row['ID'],
                    Form=row['Value'],
                    Cognateset_ID=cogid,
                    Cognate_Detection_Method='CMM')
        return

    assert method in ['sca', 'lexstat']
    try:
        lex = _cldf2lexstat(dataset)
    except ValueError:
        return
    if method == 'lexstat':
        lex.get_scorer(**kw)
    lex.cluster(method=method, threshold=threshold, ref='cogid')
    for k in lex:
        yield dict(  # pylint: disable=R1735
            Form_ID=lex[k, 'lid'],
            Form=lex[k, 'value'],
            Cognateset_ID=lex[k, 'cogid'],
            Cognate_Detection_Method=method + f'-t{threshold:.2f}')


def iter_alignments(
        dataset: Union[pycldf.Dataset, lingpy.basic.parser.QLCParser],
        cognate_sets: Iterable[dict[str, Any]],
        column: str = 'Segments',
        method: str = 'library',
        almkw: Optional[dict[str, Any]] = None,
) -> None:
    """
    Function computes automatic alignments and adds them to the cognate objects.
    """
    if not isinstance(dataset, lingpy.basic.parser.QLCParser):
        try:
            wordlist = _cldf2wordlist(dataset)
        except ValueError:
            return
        cognates = {r['Form_ID']: r for r in cognate_sets}
        wordlist.add_entries(
            'cog',
            'lid',
            lambda x: cognates[x]['Cognateset_ID'] if x in cognates else 0)
        wordlist.renumber("cog")
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
