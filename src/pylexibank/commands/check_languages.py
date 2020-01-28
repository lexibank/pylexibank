"""
Check language specifications of lexibank datasets
"""

from cldfbench.cli_util import with_datasets, add_catalog_spec
from pylexibank.cli_util import add_dataset_spec


def register(parser):
    add_dataset_spec(parser, multiple=True)
    add_catalog_spec(parser, 'glottolog')


def get_glottolog_version(cldf):
    for repo in cldf.properties.get("prov:wasDerivedFrom", []):
        if repo.get('dc:title') == 'Glottolog':
            return repo.get('dc:created')


def check(ds, args):
    args.log.info('checking {0}'.format(ds))
    cldf = ds.cldf_reader()
    if args.glottolog_version:
        gv = get_glottolog_version(cldf)
        if gv != args.glottolog_version:
            args.log.warn('Dataset compiled against Glottolog {0}'.format(gv))

    bookkeeping = set(
        l.id for l in args.glottolog.api.languoids() if l.lineage and l.lineage[0][1] == 'book1242')
    for l in cldf['LanguageTable']:
        if l['Glottocode'] and l['Glottocode'] in bookkeeping:
            args.log.warn(
                'Language {0} mapped to Bookkeeping languoid {1}'.format(l['ID'], l['Glottocode']))


def run(args):
    with_datasets(args, check)
