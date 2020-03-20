"""
Check lexibank plumbing for lexibank datasets
"""
import functools

from cldfbench.cli_util import with_datasets

from pylexibank.cli_util import add_dataset_spec, warning


def register(parser):
    add_dataset_spec(parser, multiple=True)


def check(ds, args, warnings=None):
    warn = functools.partial(warning, args, dataset=ds, warnings=warnings)

    args.log.info('checking {0} - plumbing'.format(ds))

    # check that there's no local concepts.csv:
    if (ds.dir / 'etc' / 'concepts.csv').exists():
        warn('Dataset uses a local ./etc/concepts.csv rather than a conceptlist from Concepticon')

    # check lexemes.csv
    if (ds.dir / 'etc' / 'lexemes.csv').exists():
        cldf = ds.cldf_reader()
        try:
            values = set(f['Value'] for f in cldf['FormTable'])
            for r in ds.lexemes:
                if ds.lexemes[r] and r not in values:  # replacement of form x -> y
                    warn("lexemes.csv contains un-needed conversion '{0}' -> '{1}'".format(
                        r, ds.lexemes[r]))
                if not ds.lexemes[r] and r in values:  # removal of form x -> ""
                    warn("lexemes.csv contains un-handled removal '{0}' -> '{1}'".format(
                        r, ds.lexemes[r]))
        except KeyError:
            warn('Dataset does not seem to be a lexibank dataset - FormTable has no Value column!')


def run(args):
    with_datasets(args, check)
