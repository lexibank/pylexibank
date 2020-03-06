"""
List lexibank datasets - installed or loaded into the db.
"""
import textwrap
import collections

import termcolor
from clldutils.markup import Table
from clldutils import licenses
from cldfbench.cli_util import get_datasets

from pylexibank.cli_util import add_db, get_db, add_dataset_spec

COLS = [
    'version',
    'location',
    'license',
    'changes',
    'all_lexemes',
    'lexemes',
    'concepts',
    'languages',
    'families',
    'varieties',
    'macroareas',
]


def register(parser):
    add_db(parser)
    add_dataset_spec(parser, multiple=True)
    parser.add_argument(
        '--all',
        help='Show all columns',
        action='store_true',
        default=False)
    for col in COLS:
        parser.add_argument(
            '--{0}'.format(col),
            help='Show column {0}'.format(col),
            action='store_true',
            default=False)


def run(args):
    db = get_db(args)
    in_db = {r[0]: r[1] for r in db.fetchall('select id, version from dataset')}

    table = Table('ID', 'Title')
    cols = collections.OrderedDict([
        (col, {}) for col in COLS if getattr(args, col, None) or args.all])
    tl = 40
    if cols:
        tl = 25
        table.columns.extend(col.capitalize() for col in cols)

    for col, sql in [
        ('languages', 'glottocodes_by_dataset'),
        ('concepts', 'conceptsets_by_dataset'),
        ('lexemes', 'mapped_lexemes_by_dataset'),
        ('all_lexemes', 'lexemes_by_dataset'),
        ('macroareas', 'macroareas_by_dataset'),
        ('families', 'families_by_dataset'),
    ]:
        if col in cols:
            cols[col] = {r[0]: r[1] for r in db.fetchall(sql)}
    datasets = get_datasets(args)
    for ds in datasets:
        row = [
            termcolor.colored(ds.id, 'green' if ds.id in in_db else 'red'),
            textwrap.shorten(ds.metadata.title or '', width=tl),
        ]
        for col in cols:
            if col == 'version':
                row.append(ds.repo.hash())
            elif col == 'location':
                row.append(termcolor.colored(str(ds.dir), 'green'))
            elif col == 'changes':
                row.append(ds.repo.is_dirty())
            elif col == 'license':
                lic = licenses.find(ds.metadata.license or '')
                row.append(lic.id if lic else ds.metadata.license)
            elif col in ['languages', 'concepts', 'lexemes', 'all_lexemes', 'families']:
                row.append(float(cols[col].get(ds.id, 0)))
            elif col == 'macroareas':
                row.append(', '.join(sorted((cols[col].get(ds.id) or '').split(','))))
            else:
                row.append('')

        table.append(row)
    totals = ['zztotal', len(datasets)]
    for i, col in enumerate(cols):
        if col in ['lexemes', 'all_lexemes']:
            totals.append(sum([r[i + 2] for r in table]))
        elif col == 'languages':
            totals.append(float(db.fetchone(
                "SELECT count(distinct glottocode) FROM languagetable")[0]))
        elif col == 'concepts':
            totals.append(float(db.fetchone(
                "SELECT count(distinct concepticon_id) FROM parametertable")[0]))
        elif col == 'families':
            totals.append(float(db.fetchone(
                "SELECT count(distinct family) FROM languagetable")[0]))
        else:
            totals.append('')
    table.append(totals)
    print(table.render(
        tablefmt='simple', sortkey=lambda r: r[0], condensed=False, floatfmt=',.0f'))
