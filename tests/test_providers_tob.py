from pathlib import Path
import argparse

from pylexibank.providers.tob import TOB

HTML = '<div class="results_record">' \
       '<div><span></span><span>1</span></div>' \
       '<div><span></span><span>concept</span></div>' \
       '<div>' \
       '<span>A</span>' \
       '<span class="Glottolog: abcd1234">Name</span>' \
       '<span>C</span>' \
       '<span></span>' \
       '<span>1</span>' \
       '</div>' \
       '</div>'


def test_TOB(tmpdir, mocker, concepticon, glottolog):
    class DS(TOB):
        dir = Path(str(tmpdir))
        id = 'test'
        name = 'name'
        dset = 'dset'

    tmpdir.join('metadata.json').write_text('{"conceptlist": "Wang-2004-471"}', encoding='utf8')

    class Requests(mocker.Mock):
        def get(self, *args, **kw):
            return mocker.Mock(
                status_code=200,
                iter_content=mocker.Mock(return_value=[HTML.encode('utf8')]))

    ds = DS(concepticon=concepticon, glottolog=glottolog)
    mocker.patch('cldfbench.datadir.requests', Requests())
    ds._cmd_download(mocker.Mock())
    ds._cmd_makecldf(argparse.Namespace(verbose=False, log=None, dev=False))
