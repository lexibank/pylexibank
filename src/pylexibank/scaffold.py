import pathlib

from cldfbench.scaffold import Template

import pylexibank
from pylexibank.metadata import LexibankMetadata


TEMPLATES_DIR = pathlib.Path(pylexibank.__file__).parent / 'dataset_templates'


class LexibankTemplate(Template):
    prefix = 'lexibank'
    package = pylexibank.__name__

    dirs = Template.dirs + [TEMPLATES_DIR / 'lexibank_simple']
    metadata = LexibankMetadata
