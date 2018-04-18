import logging

import pytest
from pycldf import Wordlist


@pytest.fixture
def cldf_dataset():
    return Wordlist.from_metadata('cldf/cldf-metadata.json')


@pytest.fixture
def log():
    logger = logging.getLogger('lexibank')
    logger.propagate = False
    logger.addHandler(logging.StreamHandler())
    return logger

