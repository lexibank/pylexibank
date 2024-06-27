import pytest
from csvw.metadata import Column

from pylexibank.db import Database, ColSpec, schema


@pytest.fixture
def db(tmp_path):
    return Database(tmp_path / 'lexibank.sqlite')


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


def test_db(dataset, mocker, capsys, db):
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


def test_db_multiple_datasets(dataset, dataset_cldf, dataset_cldf_capitalisation, capsys, db):
    db.load(dataset)
    db.load(dataset_cldf, verbose=True)
    db.load(dataset_cldf_capitalisation, verbose=True)
    with db.connection() as conn:
        res = db.fetchall('select `id`, `name` from LanguageTable', conn=conn)
        assert len(res) == 6
        assert ('1', 'Lang CLDF') in [(r[0], r[1]) for r in res]
        res = db.fetchall('select `id`, `value` from FormTable', conn=conn)
        assert ('1', 'abc') in [(r[0], r[1]) for r in res]


def test_db_multiple_datasets_error(dataset, dataset_factory, db):
    import shutil
    from clldutils.jsonlib import load, dump

    assert not db.fname.exists()
    db.load(dataset)

    ds_dir = dataset.dir.parent / 'dbtest'
    shutil.copytree(str(dataset.dir), str(ds_dir))
    # Now modify the CLDF data:
    md = load(ds_dir / 'cldf' / 'cldf-metadata.json')
    for t in md['tables']:
        if t['url'] == 'parameters.csv':
            for col in t['tableSchema']['columns']:
                if col['name'] == 'Chinese':
                    col['name'] = 'chinese'
                    col['datatype'] = 'integer'
    dump(md, ds_dir / 'cldf' / 'cldf-metadata.json')

    ds2 = dataset_factory('dbtest.td')
    with pytest.raises(ValueError) as e:
        db.load(ds2)
        assert 'redefined' in str(e)
