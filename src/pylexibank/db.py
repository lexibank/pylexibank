# coding: utf8
"""Functionality to load a set of CLDF datasets into a sqlite db.

Notes:
- Only CLDF components will be loaded into the db.
- The names of the columns in the database are the names from the CSV files, not the
  preferred labels for the corresponding CLDF properties.
"""
from __future__ import unicode_literals, print_function, division
from collections import OrderedDict, defaultdict
import sqlite3
from contextlib import closing
from json import dumps

from six import text_type

import attr
from csvw.datatypes import DATATYPES
from clldutils.path import Path, remove
from clldutils.misc import nfilter

from pycldf.terms import term_uri
from pycldf.sources import Sources


from pylexibank.util import git_hash


def identity(s):
    return s


TYPE_MAP = {
    'string': ('TEXT', identity),
    'integer': ('INTEGER', identity),
    'boolean': ('INTEGER', lambda s: s if s is None else int(s)),
}
BIBTEX_FIELDS = [
    'address',  # Publisher's address
    'annote',  # An annotation for annotated bibliography styles (not typical)
    'author',  # The name(s) of the author(s) (separated by and)
    'booktitle',  # The title of the book, if only part of it is being cited
    'chapter',  # The chapter number
    'crossref',  # The key of the cross-referenced entry
    'edition',  # The edition of a book, long form (such as "First" or "Second")
    'editor',  # The name(s) of the editor(s)
    'eprint',  # A specification of electronic publication, preprint or technical report
    'howpublished',  # How it was published, if the publishing method is nonstandard
    'institution',  # institution involved in the publishing,not necessarily the publisher
    'journal',  # The journal or magazine the work was published in
    'key',  # A hidden field used for specifying or overriding the orderalphabetical order
    'month',  # The month of publication (or, if unpublished, the month of creation)
    'note',  # Miscellaneous extra information
    'number',  # The "(issue) number" of a journal, magazine, or tech-report
    'organization',  # The conference sponsor
    'pages',  # Page numbers, separated either by commas or double-hyphens.
    'publisher',  # The publisher's name
    'school',  # The school where the thesis was written
    'series',  # The series of books the book was published in
    'title',  # The title of the work
    'type',  # The field overriding the default type of publication
    'url',  # The WWW address
    'volume',  # The volume of a journal or multi-volume book
    'year',
]


def insert(db, table, keys, *rows):
    if rows:
        if isinstance(keys, text_type):
            keys = [k.strip() for k in keys.split(',')]
        db.executemany(
            "INSERT INTO {0} ({1}) VALUES ({2})".format(
                table, ','.join(keys), ','.join(['?' for _ in keys])),
            rows)


def quoted(*names):
    return ','.join('`{0}`'.format(name) for name in names)


@attr.s
class ColSpec(object):
    """
    A `ColSpec` captures sufficient information about a `Column` for the DB schema.
    """
    name = attr.ib()
    csvw_type = attr.ib(default='string', convert=lambda s: s if s else 'string')
    separator = attr.ib(default=None)
    primary_key = attr.ib(default=None)
    db_type = attr.ib(default=None)
    convert = attr.ib(default=None)

    def __attrs_post_init__(self):
        if self.csvw_type in TYPE_MAP:
            self.db_type, self.convert = TYPE_MAP[self.csvw_type]
        else:
            self.db_type = 'TEXT'
            self.convert = DATATYPES[self.csvw_type].to_string

    @property
    def sql(self):
        return '`{0.name}` {0.db_type}'.format(self)


@attr.s
class TableSpec(object):
    """
    A `TableSpec` captures sufficient information about a `Table` for the DB schema.
    """
    name = attr.ib()
    columns = attr.ib(default=attr.Factory(list))
    foreign_keys = attr.ib(default=attr.Factory(list))
    consumes = attr.ib(default=None)
    primary_key = attr.ib(default=None)

    @property
    def sql(self):
        clauses = [col.sql for col in self.columns]
        clauses.append('`dataset_ID` TEXT NOT NULL')
        if self.primary_key:
            clauses.append('PRIMARY KEY(`dataset_ID`, `{0}`)'.format(self.primary_key))
        clauses.append('FOREIGN KEY(`dataset_ID`) REFERENCES dataset(`ID`)')
        for fk, ref, refcols in self.foreign_keys:
            clauses.append('FOREIGN KEY({0}) REFERENCES {1}({2})'.format(
                quoted(*fk), ref, quoted(*refcols)))
        return "CREATE TABLE {0} (\n    {1}\n)".format(self.name, ',\n    '.join(clauses))


def schema(ds):
    """
    Convert the table and column descriptions of a `Dataset` into specifications for the
    DB schema.

    :param ds:
    :return: A pair (tables, reference_tables).
    """
    tables, ref_tables = {}, {}
    table_lookup = {t.url.string: t for t in ds.tables if ds.get_tabletype(t)}
    for table in table_lookup.values():
        spec = TableSpec(ds.get_tabletype(table))
        spec.primary_key = [
            c for c in table.tableSchema.columns if
            c.propertyUrl and c.propertyUrl.uri == term_uri('id')][0].name
        for c in table.tableSchema.columns:
            if c.propertyUrl and c.propertyUrl.uri == term_uri('source'):
                # A column referencing sources is replaced by an association table.
                otype = ds.get_tabletype(table).replace('Table', '')
                ref_tables[ds.get_tabletype(table)] = TableSpec(
                    '{0}Source'.format(otype),
                    [ColSpec(otype + '_ID'), ColSpec('Source_ID'), ColSpec('Context')],
                    [
                        (
                            ['dataset_ID', otype + '_ID'],
                            ds.get_tabletype(table),
                            ['dataset_ID', spec.primary_key]),
                        (
                            ['dataset_ID', 'Source_ID'],
                            'SourceTable',
                            ['dataset_ID', 'ID']),
                    ],
                    c.name)
            else:
                spec.columns.append(ColSpec(
                    c.header,
                    c.datatype.base if c.datatype else c.datatype,
                    c.separator,
                    c.header == spec.primary_key))
        for fk in table.tableSchema.foreignKeys:
            if fk.reference.schemaReference:
                # We only support Foreign Key references between tables!
                continue  # pragma: no cover
            ref = table_lookup[fk.reference.resource.string]
            if ds.get_tabletype(ref):
                spec.foreign_keys.append((
                    tuple(['dataset_ID'] + sorted(fk.columnReference)),
                    ds.get_tabletype(table_lookup[fk.reference.resource.string]),
                    tuple(['dataset_ID'] + sorted(fk.reference.columnReference))))
        tables[spec.name] = spec

    # must determine the order in which tables must be created!
    ordered = OrderedDict()
    i = 0
    #
    # We loop through the tables repeatedly, and whenever we find one, which has all
    # referenced tables already in ordered, we move it from tables to ordered.
    #
    while tables and i < 100:
        i += 1
        for table in list(tables.keys()):
            if all(ref[1] in ordered for ref in tables[table].foreign_keys):
                # All referenced tables are already created.
                ordered[table] = tables.pop(table)
                break
    if tables:  # pragma: no cover
        raise ValueError('there seem to be cyclic dependencies between the tables')

    return list(ordered.values()), ref_tables


class Database(object):
    def __init__(self, fname):
        """
        A `Database` instance is initialized with a file path.

        :param fname: Path to a file in the file system where the db is to be stored.
        """
        self.fname = Path(fname)

    def drop(self):
        if self.fname.exists():
            remove(self.fname)

    def connection(self):
        return closing(sqlite3.connect(self.fname.as_posix()))

    def create(self, force=False, exists_ok=False):
        """
        Creates a db file with the core schema.

        :param force: If `True` an existing db file will be overwritten.
        """
        if self.fname and self.fname.exists():
            if force:
                self.drop()
            elif exists_ok:
                return
            else:
                raise ValueError('db file already exists, use force=True to overwrite')
        with self.connection() as db:
            db.execute(
                """\
CREATE TABLE dataset (
    ID TEXT PRIMARY KEY NOT NULL,
    name TEXT,
    version TEXT,
    metadata_json TEXT
)""")
            db.execute("""\
CREATE TABLE datasetmeta (
    dataset_ID TEXT ,
    key TEXT,
    value TEXT,
    PRIMARY KEY (dataset_ID, key),
    FOREIGN KEY(dataset_ID) REFERENCES dataset(ID)
)""")
            db.execute("""\
CREATE TABLE SourceTable (
    dataset_ID TEXT ,
    ID TEXT ,
    bibtex_type TEXT,
    {0}
    extra TEXT,
    PRIMARY KEY (dataset_ID, ID),
    FOREIGN KEY(dataset_ID) REFERENCES dataset(ID)
)""".format('\n    '.join('`{0}` TEXT,'.format(f) for f in BIBTEX_FIELDS)))

    def fetchone(self, sql, conn=None, verbose=False):
        return self._fetch(sql, 'fetchone', conn, verbose=verbose)

    def fetchall(self, sql, conn=None, verbose=False):
        return self._fetch(sql, 'fetchall', conn, verbose=verbose)

    def _fetch(self, sql, method, conn, verbose=False):
        sql = self.sql.get(sql, sql)

        def _do(conn, sql, method):
            cu = conn.cursor()
            if verbose:
                print(sql)
            cu.execute(sql)
            return getattr(cu, method)()

        if not conn:
            with self.connection() as conn:
                return _do(conn, sql, method)
        else:
            return _do(conn, sql, method)

    @property
    def tables(self):
        return [r[0] for r in self.fetchall(
            "SELECT name FROM sqlite_master WHERE type='table'")]

    def unload(self, dataset_id):
        dataset_id = getattr(dataset_id, 'id', dataset_id)
        with self.connection() as db:
            for table in self.tables:
                if table != 'dataset':
                    db.execute(
                        "DELETE FROM {0} WHERE dataset_ID = ?".format(table),
                        (dataset_id,))
            db.execute("DELETE FROM dataset WHERE ID = ?", (dataset_id,))
            db.commit()

    def _create_table_if_not_exists(self, table):
        if table.name in self.tables:
            return False

        with self.connection() as conn:
            conn.execute(table.sql)
        return True

    def load(self, ds):
        """
        Load a CLDF dataset into the database.

        :param dataset:
        :return:
        """
        try:
            self.fetchone('select ID from dataset')
        except sqlite3.OperationalError:
            self.create(force=True)
        self.unload(ds)
        dataset = ds.cldf.wl
        tables, ref_tables = schema(dataset)

        # update the DB schema:
        for t in tables:
            if self._create_table_if_not_exists(t):
                continue
            db_cols = {r[1]: r[2] for r in self.fetchall(
                "PRAGMA table_info({0})".format(t.name))}
            for col in t.columns:
                if col.name not in db_cols:
                    with self.connection() as conn:
                        conn.execute(
                            "ALTER TABLE {0} ADD COLUMN `{1.name}` {1.db_type}".format(
                                t.name, col))
                else:
                    if db_cols[col.name] != col.db_type:
                        raise ValueError(
                            'column {0}:{1} {2} redefined with new type {3}'.format(
                                t.name, col.name, db_cols[col.name], col.db_type))

        for t in ref_tables.values():
            self._create_table_if_not_exists(t)

        # then load the data:
        with self.connection() as db:
            db.execute('PRAGMA foreign_keys = ON;')
            insert(
                db,
                'dataset',
                'ID,name,version,metadata_json',
                (
                    ds.id,
                    '{0}'.format(dataset),
                    git_hash(ds.dir),
                    dumps(dataset.metadata_dict)))
            insert(
                db,
                'datasetmeta',
                'dataset_ID,key,value',
                *[(ds.id, k, '{0}'.format(v)) for k, v in dataset.properties.items()])

            # load sources:
            rows = []
            for src in dataset.sources.items():
                values = [ds.id, src.id, src.genre] + [src.get(k) for k in BIBTEX_FIELDS]
                values.append(
                    dumps({k: v for k, v in src.items() if k not in BIBTEX_FIELDS}))
                rows.append(tuple(values))
            insert(
                db,
                'SourceTable',
                ['dataset_ID', 'ID', 'bibtex_type'] + BIBTEX_FIELDS + ['extra'],
                *rows)

            # For regular tables, we extract and keep references to sources.
            refs = defaultdict(list)

            for t in tables:
                cols = {col.name: col for col in t.columns}
                ref_table = ref_tables.get(t.name)
                rows, keys = [], []
                for row in dataset[t.name]:
                    keys, values = ['dataset_ID'], [ds.id]
                    for k, v in row.items():
                        if ref_table and k == ref_table.consumes:
                            refs[ref_table.name].append((row[t.primary_key], v))
                        else:
                            col = cols[k]
                            if isinstance(v, list):
                                v = (col.separator or ';').join(
                                    nfilter(col.convert(vv) for vv in v))
                            else:
                                v = col.convert(v)
                            keys.append("`{0}`".format(k))
                            values.append(v)
                    rows.append(tuple(values))
                insert(db, t.name, keys, *rows)

            # Now insert the references, i.e. the associations with sources:
            for tname, items in refs.items():
                rows = []
                for oid, sources in items:
                    for source in sources:
                        sid, context = Sources.parse(source)
                        rows.append([ds.id, oid, sid, context])
                oid_col = '{0}_ID'.format(tname.replace('Source', ''))
                insert(db, tname, ['dataset_ID', oid_col, 'Source_ID', 'Context'], *rows)
            db.commit()

    def load_concepticon_data(self, concepticon):
        conceptsets = []
        for csid in self.fetchall("SELECT distinct concepticon_id FROM parametertable"):
            cs = concepticon.conceptsets.get(csid[0])
            if cs:
                conceptsets.append((cs.gloss, cs.id))

        with self.connection() as db:
            db.executemany(
                "UPDATE parametertable SET concepticon_gloss = ? WHERE concepticon_id = ?",
                conceptsets)
            db.commit()

    def load_glottolog_data(self, glottolog):
        langs = []
        languoids = {l.id: l for l in glottolog.languoids()}
        for gc in self.fetchall("SELECT distinct glottocode FROM languagetable"):
            lang = languoids.get(gc[0])
            if lang:
                langs.append((
                    lang.lineage[0][0] if lang.lineage else lang.name,
                    lang.macroareas[0].value if lang.macroareas else None,
                    lang.id))

        with self.connection() as db:
            db.executemany(
                "UPDATE languagetable "
                "SET family = ?, macroarea = ? "
                "WHERE glottocode = ?",
                langs)
            db.commit()

    sql = {
        "conceptsets_by_dataset":
            "SELECT ds.id, count(distinct p.concepticon_id) "
            "FROM dataset as ds, parametertable as p "
            "WHERE ds.id = p.dataset_id GROUP BY ds.id",
        "families_by_dataset":
            "SELECT ds.id, count(distinct l.family) "
            "FROM dataset as ds, languagetable as l "
            "WHERE ds.id = l.dataset_id GROUP BY ds.id",
        "macroareas_by_dataset":
            "SELECT ds.id, group_concat(distinct l.macroarea) "
            "FROM dataset as ds, languagetable as l "
            "WHERE ds.id = l.dataset_id GROUP BY ds.id",
        "glottocodes_by_dataset":
            "SELECT ds.id, count(distinct l.glottocode) "
            "FROM dataset as ds, languagetable as l "
            "WHERE ds.id = l.dataset_id GROUP BY ds.id",
        "mapped_lexemes_by_dataset":
            "SELECT ds.id, count(distinct f.ID) "
            "FROM dataset as ds, formtable as f, languagetable as l, parametertable as p "
            "WHERE ds.id = f.dataset_id and f.Language_ID = l.ID and "
            "f.Parameter_ID = p.ID and l.glottocode is not null and "
            "p.concepticon_id is not null "
            "GROUP BY ds.id",
        "lexemes_by_dataset":
            "SELECT ds.id, count(f.ID) FROM dataset as ds, formtable as f "
            "WHERE ds.id = f.dataset_id GROUP BY ds.id",
    }
