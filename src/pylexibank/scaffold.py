import pathlib

from cldfbench.scaffold import Template

import pylexibank
from pylexibank.metadata import LexibankMetadata


class LexibankTemplate(Template):
    prefix = 'lexibank'
    package = pylexibank.__name__

    dirs = Template.dirs + [pathlib.Path(pylexibank.__file__).parent / 'dataset_template']
    metadata = LexibankMetadata
