# coding: utf8
from __future__ import unicode_literals, print_function, division
from collections import Counter

from nose.tools import assert_equal
from clldutils.path import Path

from pylexibank import util


class MockResponse(object):
    def __init__(self, p):
        p = Path(p)
        self.status_code = 200 if p.exists() else 404
        self.path = p

    def iter_content(self, *args, **kw):
        if self.path.exists():
            with open(self.path.as_posix(), 'rb') as fp:
                yield fp.read()


class MockRequests(object):
    def __init__(self, p):
        self.path = p

    def get(self, *args, **kw):
        return MockResponse(self.path)


def test_DataDir(repos, tmppath, mocker):
    dd = util.DataDir(tmppath)
    dd.write('test.xml', '<a>b</a>')
    assert dd.read_xml('test.xml').tag == 'r'
    dd.remove('test.xml')
    dd.write('test.tsv', 'a\tb\nc\td')
    assert dd.read_tsv('test.tsv') == [['a', 'b'], ['c', 'd']]

    t = 'äöüß'
    assert t == dd.read(dd.write('test.txt', t))

    log = mocker.Mock()
    mocker.patch(
        'pylexibank.util.requests',
        MockRequests(repos / 'datasets' / 'test_dataset' / 'test.zip'))
    dd.download_and_unpack('', 'test.xlsx', log=log)
    assert log.info.called
    dd.xls2csv('test.xlsx')
    assert dd.read_csv('test.Sheet1.csv') == [['a', 'b', 'c']]


def test_split_by_year():
    assert util.split_by_year(' 2012. abc') == ('', '2012', 'abc')
    assert util.split_by_year(' (2012) abc') == ('', '2012', 'abc')
    assert util.split_by_year('abc') == (None, None, 'abc')


def test_data_path():
    assert util.data_path('abc', repos=Path('def')).as_posix().startswith('def')
    assert util.data_path('abc', repos=Path('def')).as_posix().endswith('abc')


def test_get_badge():
    for r in util.pb(list(range(10))):
        util.get_badge((r / 10.0) + 0.5, 'name')


def test_get_reference():
    assert util.get_reference('John Doe', '1998', 'The Title', None, {})
    assert util.get_reference(None, None, None, None, {}) is None
    assert util.get_reference(None, None, 'The Title', None, {}).source.id == 'thetitle'


def test_sorted_obj():
    d1 = {'a': [1, 2, 3], 'b': dict(a=3, b=1)}
    d2 = {'b': Counter('baaa'), 'a': [1, 2, 3]}
    assert_equal(util.sorted_obj(d1), util.sorted_obj(d2))
    assert_equal(util.sorted_obj(d2)['b']['a'], 3)
    util.sorted_obj(['http://www.w3.org/ns/csvw', {'@language': 'en'}])
