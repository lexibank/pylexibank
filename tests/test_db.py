# coding: utf8
from __future__ import unicode_literals, print_function, division

import pytest
from csvw.metadata import Column

from pylexibank.db import Database, ColSpec


def test_ColSpec():
    col = ColSpec(name='c', csvw_type='float')
    assert col.convert(5) == '5'


def test_db(tmpdir, dataset, mocker, capsys):
    db = Database(str(tmpdir.join('lexibank.sqlite')))
    db.load(dataset)
    db.create(exists_ok=True)
    with pytest.raises(ValueError):
        db.create()
    db.create(force=True)
    db.load(dataset)
    db.load_glottolog_data(dataset.glottolog)
    db.load_concepticon_data(mocker.Mock(conceptsets={}))
    for sql in db.sql:
        db.fetchall(sql)
    with db.connection() as conn:
        db.fetchall('select * from dataset', conn=conn, verbose=True)
    out, _ = capsys.readouterr()
    assert 'select' in out

    db.create(force=True)
    db.load(dataset)
    cols = dataset.cldf.wl['FormTable'].tableSchema.columns
    cols.append(Column(name='custom'))
    db.load(dataset)
    cols.pop()
    cols.append(Column(name='custom', datatype='integer'))
    with pytest.raises(ValueError):
        db.load(dataset)
    cols.pop()
    db.load(dataset)
