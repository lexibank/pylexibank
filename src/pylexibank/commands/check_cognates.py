"""
Check cognates table
"""
import functools
from collections import defaultdict
from cldfbench.cli_util import with_datasets, add_catalog_spec
from pylexibank.cli_util import add_dataset_spec, warning


def register(parser):
    add_dataset_spec(parser, multiple=True)
    add_catalog_spec(parser, 'glottolog')

def check(ds, args):
    warn = functools.partial(warning, args, dataset=ds)
    cldf = ds.cldf_reader()
    
    if cldf["CognateTable"].common_props.get('dc:extent') == 0:
        # NOTE: this is using the metadata to identify if we
        # have cognates or not. Is there a better way?
        return
    
    args.log.info('checking {0} - cognates'.format(ds))
    
    # do cognate sets span different words?
    # i.e. we want 'global' cognate ids so cognate sets should be 
    # found in one word/parameter only.
    cognates = {}
    for row in cldf['CognateTable']:
        cognates[row['Form_ID']] = row['Cognateset_ID']
    
    cogs_by_param = defaultdict(set)
    for row in cldf['FormTable']:
        cogset = cognates.get(row['ID'])
        if cogset:
            cogs_by_param[cogset].add(row['Parameter_ID'])
        
    for c in cogs_by_param:
        if len(cogs_by_param[c]) > 1:
            warn('Cognate set {0} is not global: {1}'.format(c, cogs_by_param[c]))
        

def run(args):
    with_datasets(args, check)
