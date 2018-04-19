# coding: utf8
from __future__ import unicode_literals, print_function, division
from collections import defaultdict, Counter, OrderedDict
from subprocess import check_call

from six import PY2
from termcolor import colored
from segments.tokenizer import Tokenizer
from clldutils import licenses
from clldutils.path import Path
from clldutils.dsv import UnicodeWriter, reader
from clldutils.markup import Table
from clldutils.clilib import command, confirm
from clldutils.text import truncate_with_ellipsis
from pyglottolog.api import Glottolog
from pybtex.database import parse_file, BibliographyData
from pyconcepticon.api import Concepticon

import pylexibank
from pylexibank.commands.util import with_dataset, get_dataset, _load, _unload
from pylexibank.util import log_dump, git_hash
from pylexibank.dataset import Dataset
from pylexibank.lingpy_util import lingpy_subset
from pylexibank.db import Database


@command()
def requirements(args):
    if args.datasets:
        print(
            '-e git+https://github.com/clld/glottolog.git@{0}#egg=pyglottolog'.format(
                git_hash(args.datasets[0].glottolog.repos)))
        print(
            '-e git+https://github.com/clld/concepticon-data.git@{0}#egg=pyconcepticon'.format(
                git_hash(args.datasets[0].concepticon.repos)))
    if pylexibank.__version__.endswith('dev0'):
        print(
            '-e git+https://github.com/lexibank/pylexibank.git@{0}#egg=pylexibank'.format(
                git_hash(Path(pylexibank.__file__).parent.parent.parent)))
    db = Database(args.db)
    db.create(exists_ok=True)
    for r in db.fetchall('select id, version from dataset'):
        print(
            '-e git+https://github.com/lexibank/{0}.git@{1}#egg=lexibank_{0}'.format(*r))


@command()
def orthography(args):  # pragma: no cover
    ds = get_dataset(args)
    out = ds.dir.joinpath('orthography.tsv')
    if out.exists():
        if not confirm(
                'There already is an orthography profile for this dataset. Overwrite?',
                default=False):
            return

    graphemes = Counter()
    for line in ds.run('lexemes'):
        graphemes.update(Tokenizer.grapheme_pattern.findall(line))

    with UnicodeWriter(out, delimiter='\t') as writer:
        writer.writerow(['graphemes', 'frequency', 'IPA'])
        for grapheme, frequency in graphemes.most_common():
            writer.writerow([grapheme, '{0}'.format(frequency), grapheme])

    log_dump(out, log=args.log)


@command()
def load(args):
    with_dataset(args, _load)


@command()
def unload(args):
    with_dataset(args, _unload)


@command()
def db(args):
    db = str(Database(args.db).fname)
    args.log.info('connecting to {0}'.format(colored(db, 'green')))
    check_call(['sqlite3', db])


@command()
def diff(args):
    def _diff(ds, **kw):
        repo = ds.git_repo
        if repo.is_dirty():
            print('{0} at {1}'.format(
                colored(ds.id, 'blue', attrs=['bold']),
                colored(str(ds.dir), 'blue')))
            for i, item in enumerate(repo.index.diff(None)):
                if i == 0:
                    print(colored('modified:', attrs=['bold']))
                print(colored(item.a_path, 'green'))
            for i, path in enumerate(repo.untracked_files):
                if i == 0:
                    print(colored('untracked:', attrs=['bold']))
                print(colored(path, 'green'))
            print()
    if not args.args:
        args.args = [ds.id for ds in args.datasets]
    with_dataset(args, _diff)


@command()
def ls(args):
    """
    lexibank ls [COLS]+

    column specification:
    - license
    - lexemes
    - macroareas
    """
    db = Database(args.db)
    db.create(exists_ok=True)
    in_db = {r[0]: r[1] for r in db.fetchall('select id, version from dataset')}
    # FIXME: how to smartly choose columns?
    table = Table('ID', 'Title')
    cols = OrderedDict([
        (col, {}) for col in args.args if col in [
            'version',
            'location',
            'changes',
            'license',
            'all_lexemes',
            'lexemes',
            'concepts',
            'languages',
            'families',
            'varieties',
            'macroareas',
        ]])
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
    for ds in args.datasets:
        row = [
            colored(ds.id, 'green' if ds.id in in_db else 'red'),
            truncate_with_ellipsis(ds.metadata.title or '', width=tl),
        ]
        for col in cols:
            if col == 'version':
                row.append(git_hash(ds.dir))
            elif col == 'location':
                row.append(colored(str(ds.dir), 'green'))
            elif col == 'changes':
                row.append(ds.git_repo.is_dirty())
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
    totals = ['zztotal', len(args.datasets)]
    for i, col in enumerate(cols):
        if col in ['lexemes', 'all_lexemes']:
            totals.append(sum([r[i + 2] for r in table]))
        elif col == 'languages':
            totals.append(float(db.fetchone(
                "SELECT count(distinct glottocode) FROM languagetable")[0]))
        elif col == 'concepts':
            totals.append(float(db.fetchone(
                "SELECT count(distinct conceptset) FROM parametertable")[0]))
        elif col == 'families':
            totals.append(float(db.fetchone(
                "SELECT count(distinct family) FROM languagetable")[0]))
        else:
            totals.append('')
    table.append(totals)
    res = table.render(
        tablefmt='simple', sortkey=lambda r: r[0], condensed=False, floatfmt=',.0f')
    if PY2:
        res = res.encode('utf8')
    print(res)


@command()
def bib(args):
    gbib = BibliographyData()

    def _harvest(ds, **kw):
        for bib in ds.cldf_dir.glob('*.bib'):
            bib = parse_file(bib.as_posix())
            for id_, entry in bib.entries.items():
                id_ = '{0}:{1}'.format(ds.id, id_)
                if id_ not in gbib.entries:
                    gbib.add_entry(id_, entry)

    with_dataset(args, _harvest)
    gbib.to_file(Path(args.cfg['paths']['lexibank']).joinpath('lexibank.bib').as_posix())


@command()
def clean(args):
    """
    Remove CLDF formatted data for given dataset.

    lexibank clean [DATASET_ID]
    """
    with_dataset(args, Dataset._clean)


# -------------------------------------------------------------------
@command()
def wordlength(args):
    import unicodedata

    concepts = Concepticon(args.cfg['paths']['concepticon']).conceptsets
    header = ['language_id', 'language_name', 'parameter_id', 'form', 'segments']
    languoids = {l.id: l for l in Glottolog(args.cfg['paths']['glottolog']).languoids()}
    languoids.update({
        'jiar1239': languoids['jiar1240'],
        'yiry1247': languoids['jirj1239'],
        'guug1239': languoids['gugu1255'],
        'miya1256': languoids['waka1283'],
    })
    ml = set()

    with UnicodeWriter('wordlength.csv') as writer, \
            UnicodeWriter('wordlength_all.csv') as writer_all:
        writer.writerow('Concepticon_ID Gloss Semanticfield Category Glottocode Variety Family Form Length'.split())
        writer_all.writerow('Concepticon_ID Gloss Semanticfield Category Glottocode Variety Family Form Length'.split())
        for ds in args.datasets:
            for mdp in ds._iter_cldf():
                csvp = mdp.parent.joinpath(mdp.name.split('-metadata')[0])
                for row in reader(csvp, dicts=True):
                    lang = languoids.get(row['Language_ID'])
                    if lang and row['Parameter_ID'] in concepts:
                        concept = concepts[row['Parameter_ID']]
                        form = unicodedata.normalize('NFC', row['Form'])
                        writer_all.writerow([
                            concept.id,
                            concept.gloss,
                            concept.semanticfield,
                            concept.ontological_category,
                            lang.id,
                            row['Language_name'],
                            languoids[lang.lineage[0][1]].name if lang.lineage else '',
                            ' '.join(form),
                            '{0}'.format(len(form)),
                        ])
                    if row['Language_ID'] and not lang:
                        ml.add(row['Language_ID'])
                for row in lingpy_subset(csvp, header):
                    lid, lname, pid, form, segments, length = row
                    lang = languoids.get(lid)
                    if not lang:
                        continue
                    concept = concepts[pid]
                    lang = languoids[lid]
                    writer.writerow([
                        concept.id,
                        concept.gloss,
                        concept.semanticfield,
                        concept.ontological_category,
                        lang.id,
                        lname,
                        languoids[lang.lineage[0][1]].name if lang.lineage else '',
                        segments,
                        length,
                    ])
    print(ml)


#  - need set of all concepts per variety.
#  - loop over concept lists
#  - if concept ids is subset of variety, count that language.
@command()
def coverage(args):  # pragma: no cover
    from pyconcepticon.api import Concepticon

    varieties = defaultdict(set)
    glangs = defaultdict(set)
    concept_count = defaultdict(set)
    res80 = Counter()
    res85 = Counter()
    res90 = Counter()
    res80v = Counter()
    res85v = Counter()
    res90v = Counter()

    def _coverage(ds, **kw):
        ds.coverage(varieties, glangs, concept_count)

    with_dataset(args, _coverage)

    print('varieties', len(varieties))

    concepticon = Concepticon(args.cfg['paths']['concepticon'])
    for cl in concepticon.conceptlists.values():
        try:
            concepts = set(
                int(cc.concepticon_id) for cc in cl.concepts.values() if cc.concepticon_id
            )
        except:
            continue
        for varid, meanings in varieties.items():
            # compute relative size of intersection instead!
            c = len(concepts.intersection(meanings)) / len(concepts)
            if c >= 0.8:
                res80v.update([cl.id])
            if c >= 0.85:
                res85v.update([cl.id])
            if c >= 0.9:
                res90v.update([cl.id])

        for varid, meanings in glangs.items():
            # compute relative size of intersection instead!
            c = len(concepts.intersection(meanings)) / len(concepts)
            if c >= 0.8:
                res80.update([cl.id])
            if c >= 0.85:
                res85.update([cl.id])
            if c >= 0.9:
                res90.update([cl.id])

    def print_count(count):
        t = Table('concept list', 'glang count')
        for p in count.most_common(n=10):
            t.append(list(p))
        print(t.render(tablefmt='simple', condensed=False))

    print('\nGlottolog languages with coverage > 80%:')
    print_count(res80)

    print('\nGlottolog languages with coverage > 85%:')
    print_count(res85)

    print('\nGlottolog languages with coverage > 90%:')
    print_count(res90)

    print('\nVarieties with coverage > 80%:')
    print_count(res80v)

    print('\nVarieties with coverage > 85%:')
    print_count(res85v)

    print('\nVarieties with coverage > 90%:')
    print_count(res90v)

    print('\ntop-200 concepts:')
    t = Table('cid', 'gloss', 'varieties')
    for n, m in sorted(
            [(cid, len(vars)) for cid, vars in concept_count.items()],
            key=lambda i: -i[1])[:200]:
        t.append([n, concepticon.conceptsets['%s' % n].gloss, m])
    print(t.render(tablefmt='simple', condensed=False))
