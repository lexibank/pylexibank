"""
Check language specifications of lexibank datasets
"""
import functools
import collections

from cldfbench.cli_util import with_datasets, add_catalog_spec
from pylexibank.cli_util import add_dataset_spec, warning


def register(parser):  # pylint: disable=C0116
    add_dataset_spec(parser, multiple=True)
    add_catalog_spec(parser, 'glottolog')


def get_glottolog_version(cldf):
    """The Glottolog version recorded in the provenance of a CLDF dataset."""
    for repo in cldf.properties.get('prov:wasDerivedFrom', []):
        if repo.get('dc:title') == 'Glottolog':
            return repo.get('dc:created')
    return None


def check(ds, args, warnings=None):
    """Check a single dataset."""
    warn = functools.partial(warning, args, dataset=ds, warnings=warnings)

    args.log.info('checking %s - languages', ds)
    cldf = ds.cldf_reader()

    # Glottolog is only available when the command is run with a Glottolog catalog, i.e. not
    # when called from `lexibank.check`.
    glottolog = getattr(args, 'glottolog', None)
    languoids, glottocode_col = {}, None
    if glottolog:
        try:
            version = glottolog.describe()
        except ValueError:  # An export of the Glottolog data rather than a git clone.
            version = None
        compiled_against = get_glottolog_version(cldf)
        if version and compiled_against and compiled_against != version:
            warn(f'Dataset was compiled against Glottolog {compiled_against}, '
                 f'but is checked against Glottolog {version}')
        languoids = glottolog.api.cached_languoids
        if ('LanguageTable', 'glottocode') in cldf:
            glottocode_col = cldf['LanguageTable', 'glottocode'].name
    id_col = cldf['LanguageTable', 'id'].name

    cols_with_values = collections.Counter()  # used for check on empty columns
    row = None
    for row in cldf['LanguageTable']:
        cols_with_values.update([key for key in row if row[key]])

        gc = row[glottocode_col] if glottocode_col else None
        if gc:
            if gc not in languoids:
                warn(f'Language {row[id_col]} has Glottocode {gc}, which is not in '
                     f'Glottolog {version or glottolog.dir}')
            elif languoids[gc].category == 'Bookkeeping':
                warn(f'Language {row[id_col]} is mapped to Bookkeeping languoid {gc}')

    # check for empty columns
    if row:
        for col in row:
            if not cols_with_values.get(col):
                warn(f'Column {col} in LanguageTable is completely empty')


def run(args):  # pylint: disable=C0116
    with_datasets(args, check)  # pragma: no cover
