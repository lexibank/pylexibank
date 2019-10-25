"""
Create an initial orthography profile, seeded from the forms created by a first run
of lexibank.makecldf.
"""
from lingpy import Wordlist
from lingpy.sequence import profile
from cldfbench.cli_util import get_dataset, add_catalog_spec
from csvw.dsv import UnicodeWriter
from clldutils.clilib import ParserError

from pylexibank.cli_util import add_dataset_spec


def register(parser):
    add_dataset_spec(parser)
    add_catalog_spec(parser, 'clts')
    parser.add_argument(
        '--context',
        action='store_true',
        help='Create orthography profile with context',
        default=False)
    parser.add_argument(
        '-f', '--force',
        action='store_true',
        help='Overwrite existing profile',
        default=False)


def run(args):
    bipa = args.clts.api.bipa
    func = profile.simple_profile
    cols = ['Grapheme', 'IPA', 'Frequence', 'Codepoints']
    kw = {'ref': 'form', 'clts': bipa}
    if args.context:
        func = profile.context_profile
        cols = ['Grapheme', 'IPA', 'Examples', 'Languages', 'Frequence', 'Codepoints']
        kw['col'] = 'language_id'

    ds = get_dataset(args)
    profile_path = ds.etc_dir / 'orthography.tsv'
    if profile_path.exists() and not args.force:
        raise ParserError('Orthography profile exists already. To overwrite, pass "-f" flag')

    header, D = [], {}
    for i, row in enumerate(ds.cldf_reader()['FormTable'], start=1):
        if i == 1:
            header = [f for f in row.keys() if f != 'ID']
            D = {0: ['lid'] + [h.lower() for h in header]}

        row['Segments'] = ' '.join(row['Segments'])
        D[i] = [row['ID']] + [row[h] for h in header]

    with UnicodeWriter(profile_path, delimiter='\t') as writer:
        writer.writerow(cols)
        for row in func(Wordlist(D, row='parameter_id', col='language_id'), **kw):
            writer.writerow(row)
    args.log.info('Orthography profile written to {0}'.format(profile_path))
