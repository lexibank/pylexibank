"""
Check language specifications of lexibank datasets
"""
import functools
import collections

from cldfbench.cli_util import with_datasets, add_catalog_spec
from pylexibank.cli_util import add_dataset_spec, warning


def register(parser):
    add_dataset_spec(parser, multiple=True)
    add_catalog_spec(parser, 'glottolog')


def get_glottolog_version(cldf):
    for repo in cldf.properties.get("prov:wasDerivedFrom", []):
        if repo.get('dc:title') == 'Glottolog':
            return repo.get('dc:created')


def check(ds, args):
    warn = functools.partial(warning, args, dataset=ds)

    args.log.info('checking {0} - languages'.format(ds))
    cldf = ds.cldf_reader()
    if args.glottolog_version:
        gv = get_glottolog_version(cldf)
        if gv != args.glottolog_version:
            warn('Dataset compiled against Glottolog {0}'.format(gv))

    bookkeeping = set(
        l.id for l in args.glottolog.api.languoids() if l.lineage and l.lineage[0][1] == 'book1242')

    cols_with_values = collections.Counter()  # used for check on empty columns
    nlanguages = 0
    for nlanguages, row in enumerate(cldf['LanguageTable'], start=1):
        # no bookkeeping languages
        gc = row[cldf['LanguageTable', 'glottocode'].name]
        if gc and gc in bookkeeping:
            warn('Language {0} mapped to Bookkeeping languoid {1}'.format(row['ID'], gc))

        cols_with_values.update([key for key in row if row[key]])

    if not nlanguages:
        warn('No languages in dataset')
        return  # and exit...

    # check for empty columns
    for col in row:
        if not cols_with_values.get(col):
            warn('Column {0} is completely empty'.format(col))


def run(args):
    with_datasets(args, check)
