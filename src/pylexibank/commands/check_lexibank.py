"""
Check lexibank plumbing for lexibank datasets
"""
import functools
import collections

from cldfbench.cli_util import with_datasets

from pylexibank.cli_util import add_dataset_spec, warning


def register(parser):
    add_dataset_spec(parser, multiple=True)


def check(ds, args, warnings=None):
    warn = functools.partial(warning, args, dataset=ds, warnings=warnings)

    args.log.info('checking {0} - plumbing'.format(ds))

    # check that there's a description of contributions:
    if not ds.get_creators_and_contributors(strict=True)[0]:
        warn('Dataset does not describe creators in {}'.format(ds.contributors_path))

    # check that there's no local concepts.csv:
    if (ds.dir / 'etc' / 'concepts.csv').exists():
        warn('Dataset uses a local ./etc/concepts.csv rather than a conceptlist from Concepticon')

    cldf = ds.cldf_reader()
    # check lexemes.csv
    if (ds.dir / 'etc' / 'lexemes.csv').exists():
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

    if (not getattr(ds, 'cross_concept_cognates', False)) and cldf.get('CognateTable'):
        # check that there are no cross-concept cognate sets:
        id_col = cldf['FormTable', 'id'].name
        pid_col = cldf['FormTable', 'parameterReference'].name
        fid_col = cldf['CognateTable', 'formReference'].name
        cogid_col = cldf['CognateTable', 'cognatesetReference'].name

        form_to_concept = {form[id_col]: form[pid_col] for form in cldf['FormTable']}
        cogset_to_concepts = collections.defaultdict(set)
        for cog in cldf['CognateTable']:
            cid = form_to_concept[cog[fid_col]]
            cogid = cog[cogid_col]
            if len(cogset_to_concepts[cogid]) == 1 \
                    and cid not in cogset_to_concepts[cogid]:
                # We warn when a second concept ID is detected for a cognateset.
                warn('Cross-concept cognate set {0}'.format(cogid))
            cogset_to_concepts[cogid].add(cid)


def run(args):
    with_datasets(args, check)
