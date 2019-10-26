import pathlib

from cldfbench.scaffold import Template

import pylexibank
from pylexibank.metadata import LexibankMetadata


_TEMPLATES_DIR = pathlib.Path(pylexibank.__file__).parent / 'dataset_templates'


class LexibankTemplate(Template):
    prefix = 'lexibank'
    package = pylexibank.__name__

    dirs = Template.dirs + [_TEMPLATES_DIR / 'lexibank_simple']
    metadata = LexibankMetadata


class LexibankCombinedTemplate(Template):
    prefix = 'lexibank'
    package = pylexibank.__name__

    dirs = Template.dirs + \
        [_TEMPLATES_DIR / 'lexibank_simple', _TEMPLATES_DIR / 'lexibank_combined']
    metadata = LexibankMetadata
