"""
CLDFBench dataset templates.
"""
import pathlib

from cldfbench.scaffold import Template

import pylexibank
from pylexibank.metadata import LexibankMetadata


_TEMPLATES_DIR = pathlib.Path(pylexibank.__file__).parent / 'dataset_templates'


class LexibankTemplate(Template):  # pylint: disable=R0903
    """Standard lexibank dataset."""
    prefix = 'lexibank'
    package = pylexibank.__name__

    dirs = Template.dirs + [_TEMPLATES_DIR / 'lexibank_simple']
    metadata = LexibankMetadata


class LexibankCombinedTemplate(Template):  # pylint: disable=R0903
    """Dataset template for multi-CLDF-dataset creation."""
    prefix = 'lexibank'
    package = pylexibank.__name__

    dirs = Template.dirs + \
        [_TEMPLATES_DIR / 'lexibank_simple', _TEMPLATES_DIR / 'lexibank_combined']
    metadata = LexibankMetadata
