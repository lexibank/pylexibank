from collections import Counter
from pathlib import Path

import pytest

from pylexibank import util


@pytest.mark.parametrize(
    'seq,subseq,repl,out',
    [
        ('abcdabcd', 'bc', 'x', list('axdaxd')),
        ([1, 2, 3, 4], [2], [9, 9], [1, 9, 9, 3, 4]),
    ]
)
def test_iter_repl(seq, subseq, repl, out):
    assert list(util.iter_repl(seq, subseq, repl)) == out


def test_jsondump(tmpdir):
    fname = str(tmpdir.join('dump.json'))
    res = util.jsondump({'a': 2}, fname)
    assert 'a' in res
    res = util.jsondump({'b': 3}, fname)
    assert res['b'] == 3 and res['a'] == 2


def test_getEvoBibAsBibtex(mocker):
    bib = '<pre>@book{key,\ntitle={The Title}\n}\n</pre>'
    mocker.patch(
        'pylexibank.util.get_url', mocker.Mock(return_value=mocker.Mock(text=bib)))
    assert '@book' in util.getEvoBibAsBibtex('')


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


def test_split_by_year():
    assert util.split_by_year(' 2012. abc') == ('', '2012', 'abc')
    assert util.split_by_year(' (2012) abc') == ('', '2012', 'abc')
    assert util.split_by_year('abc') == (None, None, 'abc')


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
    assert util.sorted_obj(d1) == util.sorted_obj(d2)
    assert util.sorted_obj(d2)['b']['a'] == 3
    util.sorted_obj(['http://www.w3.org/ns/csvw', {'@language': 'en'}])
