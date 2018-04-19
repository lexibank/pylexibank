# coding: utf8
from __future__ import unicode_literals, print_function, division

from pylexibank.db import Database


def test_db(tmpdir, dataset, mocker):
    db = Database(tmpdir.join('lexibank.sqlite'))
    db.create()
    db.load(dataset)
    db.load_glottolog_data(dataset.glottolog)
    #db.load_concepticon_data(mocker.Mock(conceptsets={}))
