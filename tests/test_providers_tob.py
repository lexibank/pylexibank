import io
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


def test_TOB(tmp_path, mocker, concepticon, glottolog):
    class DS(TOB):
        dir = tmp_path
        id = 'test'
        name = 'name'
        dset = 'dset'

    tmp_path.joinpath('metadata.json').write_text('{"conceptlist": "Wang-2004-471"}', encoding='utf8')

    class Response(io.BytesIO):
        status = 200

    ds = DS(concepticon=concepticon, glottolog=glottolog)
    mocker.patch('cldfbench.datadir.urlopen', lambda _: Response(HTML.encode('utf8')))
    ds._cmd_download(mocker.Mock())
    ds._cmd_makecldf(argparse.Namespace(verbose=False, log=None, dev=False))
