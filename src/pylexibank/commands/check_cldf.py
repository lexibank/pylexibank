"""
Check lexibank plumbing for lexibank datasets
"""
import functools

from cldfbench.cli_util import with_datasets, add_catalog_spec
from pylexibank.cli_util import add_dataset_spec, warning

def register(parser):
    add_dataset_spec(parser, multiple=True)
    add_catalog_spec(parser, 'glottolog')


def get_cldfprop_version(cldf, title):
    for repo in cldf.properties.get("prov:wasDerivedFrom", []):
        if repo.get('dc:title') == title:
            return repo.get('dc:created')


def check(ds, args):
    warn = functools.partial(warning, args, dataset=ds)

    args.log.info('checking {0} - CLDF'.format(ds))
    cldf = ds.cldf_reader()
    
    repo_version = ds.repo.hash()
    cldf_version = get_cldfprop_version(cldf, 'Repository')
    
    if not cldf_version:
        warn('Dataset has not git commit id in CLDF')
    elif repo_version != cldf_version:
        warn('Dataset compiled with different git commit id (repos={0}, cldf={1})'.format(
            repo_version,
            cldf_version
        ))


def run(args):
    with_datasets(args, check)
