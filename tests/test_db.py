# coding: utf8
from __future__ import unicode_literals, print_function, division

import pytest

from pylexibank.db import Database


def test_db(tmpdir, dataset, mocker):
    db = Database(str(tmpdir.join('lexibank.sqlite')))
    db.create()
    with pytest.raises(ValueError):
        db.create()
    db.create(force=True)
    db.create(exists_ok=True)
    db.load(dataset)
    db.load_glottolog_data(dataset.glottolog)
    db.load_concepticon_data(mocker.Mock(conceptsets={}))
