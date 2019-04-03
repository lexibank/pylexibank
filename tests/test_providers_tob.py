from pathlib import Path

from pylexibank.providers.tob import TOB

HTML = '<div class="results_record">' \
       '<div><span></span><span>number</span></div>' \
       '<div><span></span><span>concept</span></div>' \
       '<div>' \
       '<span>A</span>' \
       '<span class="Glottolog: (abcd1234)">Name</span>' \
       '<span>C</span>' \
       '<span></span>' \
       '<span>1</span>' \
       '</div>' \
       '</div>'


def test_TOB(tmpdir, mocker):
    class DS(TOB):
        dir = Path(str(tmpdir))
        id = 'test'
        name = 'name'
        dset = 'dset'

    tmpdir.join('metadata.json').write_text('{}', encoding='utf8')

    class Requests(mocker.Mock):
        def get(self, *args, **kw):
            return mocker.Mock(
                status_code=200,
                iter_content=mocker.Mock(return_value=[HTML.encode('utf8')]))

    ds = DS(concepticon=mocker.Mock(version='1'), glottolog=mocker.Mock(version='1'))
    mocker.patch(
        'pylexibank.providers.tob.getEvoBibAsBibtex',
        mocker.Mock(return_value='@misc{id,\ntitle="abc"\n}'))
    mocker.patch('pylexibank.util.requests', Requests())
    ds.cmd_download()
    ds.cmd_install()
