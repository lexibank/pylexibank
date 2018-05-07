# coding=utf-8
from __future__ import unicode_literals, print_function
from collections import defaultdict, Counter
from copy import deepcopy
import attr

import lingpy
from clldutils.misc import slug
from pyclts import TranscriptionSystem, SoundClasses
import pyclts.models

from pylexibank.dataset import Cognate

BIPA = TranscriptionSystem('bipa')
DOLGO = SoundClasses('dolgo')
SCA = SoundClasses('sca')

REPLACEMENT_MARKER = '\ufffd'


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


@attr.s
class TranscriptionAnalysis(object):
    # map segments to frequency
    segments = attr.ib(default=attr.Factory(Counter))
    # aggregate segments which are invalid for lingpy
    bipa_errors = attr.ib(default=attr.Factory(set))
    # aggregate segments which are invalid for clpa
    sclass_errors = attr.ib(default=attr.Factory(set))
    # map clpa-replaceable segments to their replacements
    replacements = attr.ib(default=defaultdict(set))
    # count number of errors
    general_errors = attr.ib(default=0)


def test_sequence(segments, analysis=None, model='dolgo'):
    """
    Test a sequence for compatibility with CLPA and LingPy.

    :param analysis: Pass a `TranscriptionAnalysis` instance for cumulative reporting.
    """
    analysis = analysis or TranscriptionAnalysis()

    # raise a ValueError in case of empty segments/strings
    if not segments:
        raise ValueError('Empty sequence.')

    # test if at least one element in `segments` has information
    # (helps to catch really badly formed input, such as ['\n']
    if not [segment for segment in segments if segment.strip()]:
        raise ValueError('No information in the sequence.')

    # build the phonologic and sound class analyses
    try:
        bipa_analysis = [BIPA[s] for s in segments]
    except:
        print(segments)
        raise
    if model == 'sca':
        soundclass_analysis = BIPA.translate(' '.join(segments), SCA).split()
    elif model == 'dolgo':
        soundclass_analysis = BIPA.translate(' '.join(segments), DOLGO).split()
    else:
        raise ValueError("Sound class model '%s' not inexistent or not implemented." % model)

    # compute general errors; this loop must take place outside the
    # following one because the code for computing single errors (either
    # in `bipa_analysis` or in `soundclass_analysis`) is unnecessary
    # complicated
    for sound_bipa, sound_class in zip(bipa_analysis, soundclass_analysis):
        if isinstance(sound_bipa, pyclts.models.UnknownSound) or sound_class == '?':
            analysis.general_errors += 1

    # iterate over the segments and analyses, updating counts of occurrences
    # and specific errors
    for segment, sound_bipa, sound_class in zip(segments, bipa_analysis, soundclass_analysis):
        # update the segment count
        analysis.segments.update([segment])

        # add an error if we got an unknown sound, otherwise just append
        # the `replacements` dictionary
        if isinstance(sound_bipa, pyclts.models.UnknownSound):
            analysis.bipa_errors.add(segment)
        else:
            analysis.replacements[sound_bipa.source].add(sound_bipa.__unicode__())

        # update sound class errors, if any
        if sound_class == '?':
            analysis.sclass_errors.add(segment)

    return segments, bipa_analysis, soundclass_analysis, analysis


def test_sequences(dataset, model='dolgo'):
    """
    Write a detailed transcription-report for a CLDF dataset in LexiBank.
    """
    analyses, bad_words, invalid_words = {}, [], []

    for i, row in enumerate(dataset['FormTable']):
        analysis = analyses.setdefault(row['Language_ID'], TranscriptionAnalysis())
        try:
            segments, _bipa, _sc, _analysis = test_sequence(
                row['Segments'], analysis=analysis, model=model)

            # update the list of `bad_words` if necessary; we precompute a
            # list of data types in `_bipa` just to make the conditional
            # checking easier
            _bipa_types = [type(s) for s in _bipa]
            if pyclts.models.UnknownSound in _bipa_types or '?' in _sc:
                bad_words.append(row)

        except ValueError:
            invalid_words.append(row)
        except AttributeError:
            print(row['Value'], row)
            raise

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
