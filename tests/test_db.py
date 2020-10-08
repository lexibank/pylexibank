import pytest
from csvw.metadata import Column

from pylexibank.db import Database, ColSpec, schema


def test_ColSpec():
    col = ColSpec(name='c', csvw_type='float')
    assert col.convert(5) == '5'


def test_schema(cldf_dataset):
    cldf_dataset['ParameterTable', 'Name'].name = 'thename'
    assert cldf_dataset['ParameterTable', 'http://cldf.clld.org/v1.0/terms.rdf#name'].header == 'thename'
    tables, reftables = schema(cldf_dataset)
    assert len(tables) == 4
    assert len(reftables) == 2
    for t in tables:
        ptschema = t.sql
        if 'ParameterTable' in ptschema:
            assert "`Name`" in ptschema
            break
    else:
        assert False


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
    cldf_ds = dataset.cldf_reader()
    cols = cldf_ds['FormTable'].tableSchema.columns
    cols.append(Column(name='custom'))
    cldf_ds.write_metadata()
    db.load(dataset)
    cols.pop()
    cols.append(Column(name='custom', datatype='integer'))
    cldf_ds.write_metadata()
    with pytest.raises(ValueError):
        db.load(dataset)
    cols.pop()
    cldf_ds.write_metadata()
    db.load(dataset)


def test_db_multiple_datasets(tmpdir, dataset, dataset_cldf, dataset_cldf_capitalisation, capsys):
    db = Database(str(tmpdir.join('lexibank.sqlite')))
    db.load(dataset)
    db.load(dataset_cldf, verbose=True)
    db.load(dataset_cldf_capitalisation, verbose=True)
    with db.connection() as conn:
        res = db.fetchall('select `id`, `name` from LanguageTable', conn=conn)
        assert len(res) == 4
        assert ('1', 'Lang CLDF') in [(r[0], r[1]) for r in res]
        res = db.fetchall('select `id`, `value` from FormTable', conn=conn)
        assert ('1', 'abc') in [(r[0], r[1]) for r in res]
