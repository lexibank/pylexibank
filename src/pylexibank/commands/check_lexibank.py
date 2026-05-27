"""
Check lexibank plumbing for lexibank datasets
"""
import functools
import collections

from cldfbench.cli_util import with_datasets

from pylexibank.cli_util import add_dataset_spec, warning


def register(parser):  # pylint: disable=C0116
    add_dataset_spec(parser, multiple=True)


def run(args):  # pylint: disable=C0116
    with_datasets(args, check)


def check(ds, args, warnings=None):
    """Check an individual dataset."""
    warn = functools.partial(warning, args, dataset=ds, warnings=warnings)

    args.log.info('checking %s - plumbing', ds)

    # check that there's a description of contributions:
    if not ds.get_creators_and_contributors(strict=True)[0]:
        warn(f'Dataset does not describe creators in {ds.contributors_path}')

    # check that there's no local concepts.csv:
    etc_concepts = ds.dir / 'etc' / 'concepts.csv'
    if etc_concepts.exists():  # pragma: no cover
        warn(f'Dataset uses {etc_concepts} rather than a conceptlist from Concepticon')

    cldf = ds.cldf_reader()
    # check lexemes.csv
    etc_lexemes = ds.dir / 'etc' / 'lexemes.csv'
    if etc_lexemes.exists():
        try:
            values = set(f['Value'] for f in cldf['FormTable'])
            for r in ds.lexemes:
                if ds.lexemes[r] and r not in values:  # replacement of form x -> y
                    warn(f"{etc_lexemes} contains un-needed conversion '{r}' -> '{ds.lexemes[r]}'")
                if not ds.lexemes[r] and r in values:  # removal of form x -> ""
                    warn(f"{etc_lexemes} contains un-handled removal '{r}' -> '{ds.lexemes[r]}'")
        except KeyError:  # pragma: no cover
            warn('Dataset does not seem to be a lexibank dataset - FormTable has no Value column!')

    if (not getattr(ds, 'cross_concept_cognates', False)) and cldf.get('CognateTable'):
        # check that there are no cross-concept cognate sets:
        form_to_concept = {
            form['id']: form['parameterReference'] for form in
            cldf.iter_rows('FormTable', 'id', 'parameterReference')}
        cogset_to_concepts = collections.defaultdict(set)
        for cog in cldf.iter_rows('CognateTable', 'formReference', 'cognatesetReference'):
            cid = form_to_concept[cog['formReference']]
            cogid = cog['cognatesetReference']
            if len(cogset_to_concepts[cogid]) == 1 \
                    and cid not in cogset_to_concepts[cogid]:
                # We warn when a second concept ID is detected for a cognateset.
                warn(f'Cross-concept cognate set {cogid}')
            cogset_to_concepts[cogid].add(cid)
