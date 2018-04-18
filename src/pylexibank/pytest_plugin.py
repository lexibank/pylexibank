import logging
from functools import partial

import pytest
from pycldf import Wordlist
from pycldf.validators import VALIDATORS


def valid_id(prefix, ds, t, c, r):
    if not r[c.name].startswith(prefix):
        raise ValueError('ID must start with "{0}"'.format(prefix))


@pytest.fixture(scope='session')
def cldf_dataset():
    ds = Wordlist.from_metadata('cldf/cldf-metadata.json')
    dsid = ds.properties.get("rdf:ID")
    if dsid:
        VALIDATORS.append((
            None, 'http://cldf.clld.org/v1.0/terms.rdf#id', partial(valid_id, dsid)))
    return ds


@pytest.fixture
def log():
    logger = logging.getLogger('lexibank')
    logger.propagate = False
    logger.addHandler(logging.StreamHandler())
    return logger
