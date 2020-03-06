"""
Check lexibank plumbing for lexibank datasets
"""
import functools

from cldfbench.cli_util import with_datasets, add_catalog_spec

from pylexibank.cli_util import add_dataset_spec, warning


def register(parser):
    add_dataset_spec(parser, multiple=True)
    add_catalog_spec(parser, 'glottolog')


def check(ds, args):
    warn = functools.partial(warning, args, dataset=ds)

    args.log.info('checking {0} - plumbing'.format(ds))

    # check that there's no local concepts.csv:
    if (ds.dir / 'etc' / 'concepts.csv').exists():
        warn('Dataset uses a local ./etc/concepts.csv rather than a conceptlist from Concepticon')

    # check for empty metadata fields:
    for field in ['citation', 'title', 'license']:
        if getattr(ds.metadata, field, None) in (None, ""):
            warn("Dataset has an empty '{0}' in metadata file".format(field))

    # check lexemes.csv
    if (ds.dir / 'etc' / 'lexemes.csv').exists():
        cldf = ds.cldf_reader()
        try:
            values = set(f['Value'] for f in cldf['FormTable'])
            for r in ds.lexemes:
                if r not in values:
                    warn("lexemes.csv contains un-needed conversion '{0}'".format(r))
        except KeyError:
            warn('Dataset does not seem to be a lexibank dataset - FormTable has no Value column!')


def run(args):
    with_datasets(args, check)
