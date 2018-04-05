# coding=utf-8
from __future__ import unicode_literals, print_function
from collections import defaultdict, Counter
from copy import deepcopy

from clldutils.misc import slug
try:
    from lingpy.sequence.sound_classes import clean_string, tokens2class
    LINGPY = True
except ImportError:  # pragma: no cover
    LINGPY = False

    def clean_string(seq, *args, **kw):
        return [seq]

    def tokens2class(seq, *args, **kw):
        return []

import lingpy as lp
from pyclpa.base import get_clpa, Unknown, Sound
import attr

from pylexibank.dataset import Cognate
from pylexibank.util import get_url

clpa = get_clpa()


def getEvoBibAsBibtex(*keys, **kw):
    """Download bibtex format and parse it from EvoBib"""
    res = []
    for key in keys:
        bib = get_url(
            "http://bibliography.lingpy.org/raw.php?key=" + key,
            log=kw.get('log')).text
        try:
            res.append('@' + bib.split('@')[1].split('</pre>')[0])
        except IndexError:
            res.append('@misc{'+key+',\nNote={missing source}\n\n}')
    return '\n\n'.join(res)


def wordlist2cognates(wordlist, source, expert='expert', ref='cogid'):
    """Turn a wordlist into a cognate set list, using the cldf parameters."""
    for k in wordlist:
        yield dict(
            Word_ID=wordlist[k, 'lid'],
            Index=k,
            Form=wordlist[k, 'ipa'],
            Cognateset_ID='{0}-{1}'.format(
                slug(wordlist[k, 'concept']), wordlist[k, ref]),
            Cognate_detection_method=expert,
            Cognate_source=source)


@attr.s
class TranscriptionAnalysis(object):
    # map segments to frequency
    segments = attr.ib(default=attr.Factory(Counter))
    # aggregate segments which are invalid for lingpy
    lingpy_errors = attr.ib(default=attr.Factory(set))
    # aggregate segments which are invalid for clpa
    clpa_errors = attr.ib(default=attr.Factory(set))
    # map clpa-replaceable segments to their replacements
    replacements = attr.ib(default=defaultdict(set))
    # count number of errors
    general_errors = attr.ib(default=0)


class InvalidString(Exception):
    pass


def test_sequence(segments, analysis=None, model='dolgo', **keywords):
    """
    Test a sequence for compatibility with CLPA and LingPy.

    :param analysis: Pass a `TranscriptionAnalysis` instance for cumulative reporting.
    """
    analysis = analysis or TranscriptionAnalysis()

    # clean the string at first, we only take the first item, ignore the rest
    try:
        if not isinstance(segments, list):
            segments = clean_string(segments, **keywords)[0].split(' ')
        lingpy_analysis = [
            x if y != '0' else '?' for x, y in
            zip(segments, tokens2class(segments, model))]
        clpa_analysis = clpa(segments)
        for l, c in zip(lingpy_analysis, clpa_analysis):
            if l == '?' or isinstance(c, Unknown):
                analysis.general_errors += 1
    except (ValueError, IndexError, AttributeError, TypeError, AssertionError):
        raise InvalidString()

    for a, b, c in zip(segments, lingpy_analysis, clpa_analysis):
        if a[0] in clpa.accents:
            a = a[1:]
        analysis.segments.update([a])
        if b == '?':
            analysis.lingpy_errors.add(a)
        if isinstance(c, Unknown):
            analysis.clpa_errors.add(a)
        if isinstance(c, Sound) and c.converted:
            analysis.replacements[c.origin].add(c.clpa.CLPA)

    return segments, lingpy_analysis, ['%s' % x for x in clpa_analysis], analysis


def segmentize(string, clean=lambda s: s, **kw):
    """
    Write a detailed transcription-report for a CLDF dataset in LexiBank.
    """
    try:
        return test_sequence(clean(string), segmentized=False, **kw)[0]
    except InvalidString:
        pass


def test_sequences(dataset,
                   lid_getter,
                   model='dolgo'):
    """
    Write a detailed transcription-report for a CLDF dataset in LexiBank.
    """
    analyses, bad_words, invalid_words = {}, [], []

    for i, row in enumerate(dataset['FormTable']):
        analysis = analyses.setdefault(lid_getter(row), TranscriptionAnalysis())
        try:
            segments, _lpa, _clpa, _analysis = test_sequence(
                row['Segments'], analysis=analysis, model=model)
            if '?' in _lpa or '\ufffd' in _clpa:
                bad_words.append(row)
        except InvalidString:
            invalid_words.append(row)

    return analyses, bad_words, invalid_words


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
        row='parameter_name',
        col='language_name'):
    """Read LexStat object from cldf dataset."""
    D = _cldf2wld(dataset)
    return lp.LexStat(D, segments=segments, transcription=transcription, row=row, col=col)


def _cldf2wordlist(dataset, row='parameter_id', col='language_id'):
    """Read worldist object from cldf dataset."""
    return lp.Wordlist(_cldf2wld(dataset), row=row, col=col)


def iter_cognates(dataset, column='Segments', method='turchin', threshold=0.5, **kw):
    """
    Compute cognates automatically for a given dataset.
    """
    if method == 'turchin':
        for row in dataset.objects['FormTable']:
            sounds = ''.join(tokens2class(row[column], 'dolgo'))
            if sounds.startswith('V'):
                sounds = 'H' + sounds
            sounds = '-'.join([s for s in sounds if s != 'V'][:2])
            cogid = slug(row.get('Parameter_name') or row['Parameter_ID'])+'-'+sounds
            if '0' not in sounds:
                yield dict(
                    Word_ID=row['ID'],
                    Form=row['Value'],
                    Cognateset_ID=cogid,
                    Cognate_detection_method='CMM')

    if method in ['sca', 'lexstat']:
        lex = _cldf2lexstat(dataset)
        if method == 'lexstat':
            lex.get_scorer(**kw)
        lex.cluster(method=method, threshold=threshold, ref='cogid')
        for k in lex:
            yield Cognate(
                Word_ID=lex[k, 'lid'],
                Form=lex[k, 'value'],
                Cognateset_ID=lex[k, 'cogid'],
                Cognate_detection_method=method + '-t{0:.2f}'.format(threshold))


def iter_alignments(dataset, cognate_sets, column='Segments', method='library'):
    """
    Function computes automatic alignments and writes them to file.
    """
    if not isinstance(dataset, lp.basic.parser.QLCParser):
        wordlist = _cldf2wordlist(dataset)
        cognates = {r['Word_ID']: r for r in cognate_sets}
        wordlist.add_entries(
            'cogid',
            'lid',
            lambda x: cognates[x]['Cognateset_ID'] if x in cognates else '')
        for i, k in enumerate(wordlist):
            if not wordlist[k, 'cogid']:
                wordlist[k][wordlist.header['cogid']] = 'empty-%s' % i
        alm = lp.Alignments(
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
                cognate['Alignment_method'] = method
    else:
        alm = lp.Alignments(dataset, ref='cogid')
        alm.align(method=method)

        for cognate in cognate_sets:
            idx = cognate['Index']
            if idx is None:
                idx = int(cognate['Word_ID'].split('-')[-1])
            cognate['Alignment'] = alm[idx, 'alignment'].split(' ')
            cognate['Alignment_method'] = 'SCA-'+method


def lingpy_subset(path, header, errors=2):
    try:
        wl = lp.get_wordlist(path, col='language_name', row='parameter_name')
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
                cv = lp.tokens2class(segments.split(), 'cv')
                if '0' in cv:
                    error_count += 1
                else:
                    l = sum(1 for x in cv if x != 'T')
                    if l:
                        goodlist += [(idx, l)]
                if error_count > errors:
                    goodlist = []
                    break
        for idx, l in goodlist:
            data.append([wl[idx, h] for h in header] + ['{0}'.format(l)])
    return data
